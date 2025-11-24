import React, { useState } from 'react';
import './Login.css';

const Login = ({ onLogin }) => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Get password from environment variable or use default
  const CORRECT_PASSWORD = process.env.REACT_APP_DASHBOARD_PASSWORD || 'metastacker2024';

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Simple password check
    if (password === CORRECT_PASSWORD) {
      // Store authentication in localStorage
      localStorage.setItem('dashboard_authenticated', 'true');
      localStorage.setItem('dashboard_auth_timestamp', Date.now().toString());
      onLogin();
    } else {
      setError('Incorrect password. Please try again.');
      setPassword('');
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <div className="login-header">
          <h1>🚀 MetaStackerBandit</h1>
          <p>Dashboard Access</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              autoFocus
              disabled={loading}
              required
            />
          </div>

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <button 
            type="submit" 
            className="login-button"
            disabled={loading || !password}
          >
            {loading ? 'Verifying...' : 'Login'}
          </button>
        </form>

        <div className="login-footer">
          <p>Protected Dashboard</p>
        </div>
      </div>
    </div>
  );
};

export default Login;

