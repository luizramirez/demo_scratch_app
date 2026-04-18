import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import useForm from '../hooks/useForm';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showChangePassword, setShowChangePassword] = useState(false);
  const { values, submitting, serverError, success, setSuccess, handleChange, handleSubmit } =
    useForm({ currentPassword: '', password: '', confirm: '' });

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const onChangePassword = handleSubmit(async ({ currentPassword, password, confirm }) => {
    if (password !== confirm) throw new Error('New passwords do not match');
    await api.put('/auth/change-password', { currentPassword, password });
    setSuccess('Password changed. Please sign in again.');
    await logout();
    setTimeout(() => navigate('/login'), 2000);
  });

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Auth App</h1>
        <div className="header-user">
          <span>{user?.name}</span>
          <button onClick={handleLogout} className="btn btn-outline btn-sm">
            Sign out
          </button>
        </div>
      </header>

      <main className="dashboard-main">
        <div className="card">
          <h2>Your profile</h2>
          <dl className="profile-list">
            <dt>Name</dt>
            <dd>{user?.name}</dd>
            <dt>Email</dt>
            <dd>
              {user?.email}{' '}
              {user?.isEmailVerified ? (
                <span className="badge badge-success">Verified</span>
              ) : (
                <span className="badge badge-warning">Unverified</span>
              )}
            </dd>
            <dt>Member since</dt>
            <dd>{new Date(user?.createdAt).toLocaleDateString()}</dd>
          </dl>
        </div>

        <div className="card">
          <div className="card-header">
            <h2>Security</h2>
            <button
              className="btn btn-outline btn-sm"
              onClick={() => setShowChangePassword((v) => !v)}
            >
              {showChangePassword ? 'Cancel' : 'Change password'}
            </button>
          </div>

          {showChangePassword && (
            <form onSubmit={onChangePassword} noValidate style={{ marginTop: '1rem' }}>
              {success && <div className="alert alert-success">{success}</div>}
              {serverError && <div className="alert alert-error">{serverError}</div>}

              <div className="form-group">
                <label htmlFor="currentPassword">Current password</label>
                <input
                  id="currentPassword"
                  name="currentPassword"
                  type="password"
                  value={values.currentPassword}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="password">New password</label>
                <input
                  id="password"
                  name="password"
                  type="password"
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
                  value={values.confirm}
                  onChange={handleChange}
                  required
                />
              </div>

              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? 'Updating…' : 'Update password'}
              </button>
            </form>
          )}
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
