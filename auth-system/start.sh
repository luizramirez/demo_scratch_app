#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# ── MongoDB (Docker) ───────────────────────────────────────────────────────
echo "Starting MongoDB..."
CONTAINER="auth-mongo"
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  echo "  MongoDB container already running"
elif docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  docker start "$CONTAINER" >/dev/null
  echo "  MongoDB container restarted"
else
  docker run -d --name "$CONTAINER" -p 27017:27017 mongo:7 >/dev/null
  echo "  MongoDB container created"
fi
echo "  Waiting for MongoDB to be ready..."
for i in {1..15}; do
  docker exec "$CONTAINER" mongosh --quiet --eval "db.runCommand({ping:1})" >/dev/null 2>&1 && break
  sleep 1
done
echo "  MongoDB ready"

# ── Express server ─────────────────────────────────────────────────────────
echo "Starting Express server..."
cd "$ROOT/server"
node server.js &
SERVER_PID=$!
echo "  Express PID: $SERVER_PID"

# Wait for Express to be ready
for i in {1..10}; do
  curl -s http://localhost:5001/api/auth/me >/dev/null 2>&1 && break
  sleep 1
done
echo "  Express ready on http://localhost:5001"

# ── React client ───────────────────────────────────────────────────────────
echo "Starting React client..."
cd "$ROOT/client"
npm start &
CLIENT_PID=$!
echo "  React PID: $CLIENT_PID"

echo ""
echo "All services started. App: http://localhost:3000"
echo "Press Ctrl+C to stop everything."

# Trap Ctrl+C and kill all child processes
trap "echo ''; echo 'Stopping...'; kill $SERVER_PID $CLIENT_PID 2>/dev/null; exit 0" INT TERM

wait
