import { Link, useParams, useNavigate } from 'react-router-dom';
import api from '../utils/api';
import useForm from '../hooks/useForm';

const ResetPassword = () => {
  const { token } = useParams();
  const navigate = useNavigate();
  const { values, submitting, serverError, success, setSuccess, handleChange, handleSubmit } =
    useForm({ password: '', confirm: '' });

  const onSubmit = handleSubmit(async ({ password, confirm }) => {
    if (password !== confirm) throw new Error('Passwords do not match');
    await api.post(`/auth/reset-password/${token}`, { password });
    setSuccess('Password reset! Redirecting to login…');
    setTimeout(() => navigate('/login'), 2000);
  });

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1 className="auth-title">Reset password</h1>

        <form onSubmit={onSubmit} noValidate>
          {success && <div className="alert alert-success">{success}</div>}
          {serverError && <div className="alert alert-error">{serverError}</div>}

          <div className="form-group">
            <label htmlFor="password">New password</label>
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

          <div className="form-group">
            <label htmlFor="confirm">Confirm new password</label>
            <input
              id="confirm"
              name="confirm"
              type="password"
              autoComplete="new-password"
              value={values.confirm}
              onChange={handleChange}
              placeholder="Repeat your new password"
              required
            />
          </div>

          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? 'Resetting…' : 'Reset password'}
          </button>
        </form>

        <p className="text-center" style={{ marginTop: '1rem' }}>
          <Link to="/login">Back to sign in</Link>
        </p>
      </div>
    </div>
  );
};

export default ResetPassword;
