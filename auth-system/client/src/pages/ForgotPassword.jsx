import { Link } from 'react-router-dom';
import api from '../utils/api';
import useForm from '../hooks/useForm';

const ForgotPassword = () => {
  const { values, submitting, serverError, success, setSuccess, handleChange, handleSubmit } =
    useForm({ email: '' });

  const onSubmit = handleSubmit(async ({ email }) => {
    const { data } = await api.post('/auth/forgot-password', { email });
    setSuccess(data.message);
  });

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1 className="auth-title">Forgot password</h1>
        <p className="auth-subtitle">
          Enter your email and we'll send a reset link.
        </p>

        <form onSubmit={onSubmit} noValidate>
          {success && <div className="alert alert-success">{success}</div>}
          {serverError && <div className="alert alert-error">{serverError}</div>}

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

          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? 'Sending…' : 'Send reset link'}
          </button>
        </form>

        <p className="text-center" style={{ marginTop: '1rem' }}>
          <Link to="/login">Back to sign in</Link>
        </p>
      </div>
    </div>
  );
};

export default ForgotPassword;
