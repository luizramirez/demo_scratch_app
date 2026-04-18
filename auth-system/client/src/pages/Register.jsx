import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import useForm from '../hooks/useForm';

const Register = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const { values, submitting, serverError, success, setSuccess, handleChange, handleSubmit } =
    useForm({ name: '', email: '', password: '' });

  const onSubmit = handleSubmit(async ({ name, email, password }) => {
    await register(name, email, password);
    setSuccess('Account created! Check your email to verify your account.');
  });

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1 className="auth-title">Create an account</h1>
        <p className="auth-subtitle">Already have an account? <Link to="/login">Sign in</Link></p>

        <form onSubmit={onSubmit} noValidate>
          {success && <div className="alert alert-success">{success}</div>}
          {serverError && <div className="alert alert-error">{serverError}</div>}

          <div className="form-group">
            <label htmlFor="name">Full name</label>
            <input
              id="name"
              name="name"
              type="text"
              autoComplete="name"
              value={values.name}
              onChange={handleChange}
              placeholder="Jane Doe"
              required
            />
          </div>

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
              autoComplete="new-password"
              value={values.password}
              onChange={handleChange}
              placeholder="Min. 8 chars, upper, lower & number"
              required
            />
          </div>

          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Register;
