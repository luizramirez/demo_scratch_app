import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../utils/api';

const VerifyEmail = () => {
  const { token } = useParams();
  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    api
      .get(`/auth/verify-email/${token}`)
      .then(({ data }) => {
        setMessage(data.message);
        setStatus('success');
      })
      .catch((err) => {
        setMessage(err.response?.data?.message || 'Verification failed');
        setStatus('error');
      });
  }, [token]);

  return (
    <div className="auth-container">
      <div className="auth-card text-center">
        {status === 'loading' && (
          <>
            <div className="spinner" style={{ margin: '0 auto 1rem' }} />
            <p>Verifying your email…</p>
          </>
        )}
        {status === 'success' && (
          <>
            <div className="icon-success">✓</div>
            <h1 className="auth-title">Email verified!</h1>
            <p>{message}</p>
            <Link to="/login" className="btn btn-primary" style={{ display: 'inline-block', marginTop: '1rem' }}>
              Sign in
            </Link>
          </>
        )}
        {status === 'error' && (
          <>
            <div className="icon-error">✕</div>
            <h1 className="auth-title">Verification failed</h1>
            <p>{message}</p>
            <Link to="/login" className="btn btn-primary" style={{ display: 'inline-block', marginTop: '1rem' }}>
              Back to sign in
            </Link>
          </>
        )}
      </div>
    </div>
  );
};

export default VerifyEmail;
