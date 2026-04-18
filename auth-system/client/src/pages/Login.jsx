import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import useForm from '../hooks/useForm';

const Login = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || '/dashboard';

  const { values, submitting, serverError, handleChange, handleSubmit } = useForm({
    email: '',
    password: '',
  });

  const onSubmit = handleSubmit(async ({ email, password }) => {
    await login(email, password);
    navigate(from, { replace: true });
  });

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1 className="auth-title">Sign in</h1>
        <p className="auth-subtitle">
          No account? <Link to="/register">Create one</Link>
        </p>

        <form onSubmit={onSubmit} noValidate>
          {serverError && (
            <div className="alert alert-error">
              {serverError}
              {serverError.includes('verify') && (
                <> — <Link to="/resend-verification">Resend verification email</Link></>
              )}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              value={values.email}
              onChange={handleChange}
              placeholder="jane@example.com"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={values.password}
              onChange={handleChange}
              placeholder="Your password"
              required
            />
          </div>

          <div className="form-row">
            <Link to="/forgot-password" className="link-muted">
              Forgot password?
            </Link>
          </div>

          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Login;
