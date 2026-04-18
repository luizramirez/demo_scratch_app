from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime, timezone

app = Flask(__name__)

METAR_API = "https://aviationweather.gov/api/data/metar"

WIND_DIRS = [
    "North", "North-Northeast", "Northeast", "East-Northeast",
    "East", "East-Southeast", "Southeast", "South-Southeast",
    "South", "South-Southwest", "Southwest", "West-Southwest",
    "West", "West-Northwest", "Northwest", "North-Northwest"
]

CLOUD_DESCRIPTIONS = {
    "SKC": "clear skies",
    "CLR": "clear skies",
    "CAVOK": "clear skies, excellent visibility",
    "FEW": "a few clouds",
    "SCT": "scattered clouds",
    "BKN": "mostly cloudy (broken)",
    "OVC": "overcast (completely cloudy)",
    "VV": "sky obscured",
}

WEATHER_CODES = {
    "RA": "rain", "SN": "snow", "DZ": "drizzle", "GR": "hail",
    "GS": "small hail", "IC": "ice crystals", "PL": "ice pellets",
    "SG": "snow grains", "UP": "unknown precipitation",
    "FG": "fog", "BR": "mist", "HZ": "haze", "FU": "smoke",
    "DU": "dust", "SA": "sand", "VA": "volcanic ash",
    "SQ": "squalls", "PO": "dust whirls", "DS": "duststorm",
    "SS": "sandstorm", "FC": "funnel cloud / tornado",
    "TS": "thunderstorm", "SHRA": "rain showers", "SHSN": "snow showers",
    "TSRA": "thunderstorm with rain", "FZRA": "freezing rain",
    "FZDZ": "freezing drizzle", "FZFG": "freezing fog",
    "RASN": "rain and snow mix", "-": "light", "+": "heavy",
}

def degrees_to_compass(degrees):
    if degrees is None:
        return "variable"
    idx = round(degrees / 22.5) % 16
    return WIND_DIRS[idx]

def celsius_to_fahrenheit(c):
    if c is None:
        return None
    return round(c * 9 / 5 + 32)

def knots_to_mph(knots):
    if knots is None:
        return None
    return round(knots * 1.15078)

def decode_visibility(vis_str):
    if vis_str is None:
        return "unknown"
    if str(vis_str).endswith("+"):
        return f"more than {vis_str[:-1]} miles"
    try:
        val = float(vis_str)
        if val >= 10:
            return "10+ miles (excellent)"
        elif val >= 5:
            return f"{val} miles (good)"
        elif val >= 3:
            return f"{val} miles (moderate)"
        elif val >= 1:
            return f"{val} miles (reduced)"
        else:
            return f"{val} miles (poor)"
    except (ValueError, TypeError):
        return str(vis_str) + " miles"

def decode_clouds(clouds, wx_string):
    if not clouds:
        return "clear skies"
    parts = []
    for layer in clouds:
        cover = layer.get("cover", "")
        base = layer.get("base")
        desc = CLOUD_DESCRIPTIONS.get(cover, cover)
        if base:
            parts.append(f"{desc} at {base:,} ft")
        else:
            parts.append(desc)
    return "; ".join(parts) if parts else "clear skies"

def decode_weather(wx_string):
    if not wx_string:
        return None
    result = []
    for code, meaning in WEATHER_CODES.items():
        if code in wx_string:
            result.append(meaning)
    if result:
        seen = []
        for r in result:
            if r not in seen:
                seen.append(r)
        return ", ".join(seen)
    return wx_string

def overall_condition(clouds, wx_string, vis_str):
    wx = decode_weather(wx_string)
    if wx:
        return wx.capitalize()
    if not clouds:
        return "Clear"
    top_cover = clouds[0].get("cover", "") if clouds else ""
    if top_cover in ("SKC", "CLR", "CAVOK"):
        return "Clear"
    elif top_cover == "FEW":
        return "Mostly clear"
    elif top_cover == "SCT":
        return "Partly cloudy"
    elif top_cover == "BKN":
        return "Mostly cloudy"
    elif top_cover == "OVC":
        return "Overcast"
    return "Mixed conditions"

def condition_emoji(condition, wx_string):
    wx = (wx_string or "").upper()
    cond = condition.lower()
    if "thunder" in cond or "TS" in wx:
        return "⛈️"
    if "snow" in cond or "SN" in wx:
        return "❄️"
    if "freezing" in cond or "FZ" in wx:
        return "🌨️"
    if "rain" in cond or "RA" in wx or "DZ" in wx:
        return "🌧️"
    if "fog" in cond or "FG" in wx or "mist" in cond or "BR" in wx:
        return "🌫️"
    if "haze" in cond or "HZ" in wx:
        return "😶‍🌫️"
    if "overcast" in cond:
        return "☁️"
    if "mostly cloudy" in cond:
        return "🌥️"
    if "partly cloudy" in cond or "scattered" in cond:
        return "⛅"
    return "☀️"

def format_time(obs_time):
    try:
        dt = datetime.fromtimestamp(obs_time, tz=timezone.utc)
        return dt.strftime("%B %d, %Y at %H:%Mz (UTC)")
    except Exception:
        return "Unknown time"

def build_friendly_summary(data):
    temp_c = data.get("temp")
    dewp_c = data.get("dewp")
    wdir = data.get("wdir")
    wspd = data.get("wspd")
    wgst = data.get("wgst")
    visib = data.get("visib")
    altim = data.get("altim")
    wx_string = data.get("wxString")
    clouds = data.get("clouds", [])
    obs_time = data.get("obsTime")
    name = data.get("name", "Unknown Airport")
    icao = data.get("icaoId", "")

    temp_f = celsius_to_fahrenheit(temp_c)
    dewp_f = celsius_to_fahrenheit(dewp_c)
    wspd_mph = knots_to_mph(wspd)
    wgst_mph = knots_to_mph(wgst)
    compass = degrees_to_compass(wdir)
    condition = overall_condition(clouds, wx_string, visib)
    emoji = condition_emoji(condition, wx_string)

    wind_desc = "Calm"
    if wspd and wspd > 0:
        wind_desc = f"From the {compass} at {wspd_mph} mph"
        if wgst_mph:
            wind_desc += f", gusting to {wgst_mph} mph"

    cloud_desc = decode_clouds(clouds, wx_string)
    vis_desc = decode_visibility(visib)
    wx_desc = decode_weather(wx_string)

    summary = {
        "airport_name": name,
        "icao": icao,
        "observed": format_time(obs_time),
        "emoji": emoji,
        "condition": condition,
        "temperature": f"{temp_f}°F / {temp_c}°C" if temp_f is not None else "Unknown",
        "dewpoint": f"{dewp_f}°F / {dewp_c}°C" if dewp_f is not None else "Unknown",
        "wind": wind_desc,
        "visibility": vis_desc,
        "clouds": cloud_desc,
        "weather": wx_desc,
        "altimeter": f"{altim:.2f} inHg" if altim else "Unknown",
        "raw": data.get("rawOb", ""),
        "headline": build_headline(condition, temp_f, wspd_mph, compass, wx_desc),
    }
    return summary

def build_headline(condition, temp_f, wspd_mph, compass, wx_desc):
    parts = []
    if wx_desc:
        parts.append(wx_desc.capitalize())
    else:
        parts.append(condition)
    if temp_f is not None:
        parts.append(f"{temp_f}°F")
    if wspd_mph and wspd_mph > 0:
        parts.append(f"winds {wspd_mph} mph from the {compass}")
    elif wspd_mph == 0:
        parts.append("calm winds")
    return ", ".join(parts)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/metar/<code>")
def get_metar(code):
    code = code.upper().strip()
    if not (2 <= len(code) <= 4 and code.isalpha()):
        return jsonify({"error": "Please enter a valid 3- or 4-letter airport code (e.g. KJFK or LAX)."}), 400

    try:
        resp = requests.get(
            METAR_API,
            params={"ids": code, "format": "json"},
            timeout=10,
        )
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return jsonify({"error": "The weather service took too long to respond. Please try again."}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Could not reach the weather service: {str(e)}"}), 502

    try:
        results = resp.json()
    except ValueError:
        return jsonify({"error": "Received an unexpected response from the weather service."}), 502

    if not results:
        return jsonify({
            "error": f"No METAR data found for '{code}'. Check the airport code and try again."
        }), 404

    summary = build_friendly_summary(results[0])
    return jsonify(summary)


if __name__ == "__main__":
    app.run(debug=True)
