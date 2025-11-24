import React, { useState, useEffect } from 'react';
import './App.css';
import Dashboard from './components/Dashboard';
import BotStatus from './components/BotStatus';
import EquityChart from './components/EquityChart';
import SignalsTable from './components/SignalsTable';
import HealthMetrics from './components/HealthMetrics';
import ExecutionsTable from './components/ExecutionsTable';
import LogViewer from './components/LogViewer';
import Login from './components/Login';

// Use empty string for relative paths in production, localhost for dev
// If REACT_APP_API_URL is explicitly set to empty string, use it (for relative paths)
// Otherwise default to localhost for development
const API_BASE = process.env.REACT_APP_API_URL === '' ? '' : (process.env.REACT_APP_API_URL || 'http://localhost:8000');

// Check if user is authenticated
const checkAuth = () => {
  const authenticated = localStorage.getItem('dashboard_authenticated');
  const timestamp = localStorage.getItem('dashboard_auth_timestamp');
  
  if (!authenticated || authenticated !== 'true') {
    return false;
  }
  
  // Optional: Add session timeout (24 hours)
  if (timestamp) {
    const hoursSinceLogin = (Date.now() - parseInt(timestamp)) / (1000 * 60 * 60);
    if (hoursSinceLogin > 24) {
      localStorage.removeItem('dashboard_authenticated');
      localStorage.removeItem('dashboard_auth_timestamp');
      return false;
    }
  }
  
  return true;
};

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(checkAuth());
  const [selectedBot, setSelectedBot] = useState('5m');
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isAuthenticated) {
      fetchDashboardData();
      const interval = setInterval(fetchDashboardData, 5000); // Update every 5 seconds
      return () => clearInterval(interval);
    }
  }, [isAuthenticated]);

  const fetchDashboardData = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/dashboard/summary`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setDashboardData(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      // Set default structure to prevent crashes
      setDashboardData({ bots: {}, total_equity: 0, total_signals: 0 });
      setLoading(false);
    }
  };

  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('dashboard_authenticated');
    localStorage.removeItem('dashboard_auth_timestamp');
    setIsAuthenticated(false);
  };

  // Show login page if not authenticated
  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <h1>🚀 MetaStackerBandit Dashboard</h1>
          <div className="header-status">
            {dashboardData && (
              <span className="status-indicator">
                Last Update: {new Date(dashboardData.last_update).toLocaleTimeString()}
              </span>
            )}
            {process.env.REACT_APP_BUILD_TIMESTAMP && (
              <span className="status-indicator" style={{ fontSize: '0.75rem', opacity: 0.7 }}>
                Build: {process.env.REACT_APP_BUILD_TIMESTAMP.substring(0, 8)}
              </span>
            )}
            <button 
              onClick={handleLogout}
              className="logout-button"
              title="Logout"
            >
              🚪 Logout
            </button>
          </div>
        </div>
      </header>

      <div className="main-container">
        <div className="sidebar">
          <BotStatus 
            bots={(dashboardData && dashboardData.bots) ? dashboardData.bots : {}}
            selectedBot={selectedBot}
            onSelectBot={setSelectedBot}
            loading={loading}
          />
        </div>

        <div className="content">
          {loading ? (
            <div className="loading">Loading dashboard data...</div>
          ) : (
            <>
              <Dashboard summary={dashboardData} />
              
              <div className="bot-content">
                {selectedBot === 'logs' ? (
                  <div className="chart-section">
                    <LogViewer />
                  </div>
                ) : (
                  <>
                    <div className="chart-section">
                      <EquityChart botVersion={selectedBot} />
                    </div>

                    <div className="metrics-grid">
                      <div className="metric-card">
                        <h3>Health Metrics</h3>
                        <HealthMetrics botVersion={selectedBot} />
                      </div>

                      <div className="metric-card">
                        <h3>Recent Signals</h3>
                        <SignalsTable botVersion={selectedBot} />
                      </div>

                      {(selectedBot === '5m' || selectedBot === '24h') && (
                        <div className="metric-card">
                          <h3>Executions</h3>
                          <ExecutionsTable botVersion={selectedBot} />
                        </div>
                      )}

                      <div className="metric-card full-width">
                        <h3>Logs & Emitters</h3>
                        <LogViewer botVersion={selectedBot} showBotFilter={false} />
                      </div>
                    </div>
                  </>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;

