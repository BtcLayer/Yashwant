import React from 'react';
import './Dashboard.css';

const Dashboard = ({ summary }) => {
  if (!summary || !summary.bots) {
    return (
      <div className="dashboard-summary">
        <div className="loading">Loading dashboard data...</div>
      </div>
    );
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value || 0);
  };

  // Safely get bot data with fallbacks
  const getBotData = (version) => {
    return summary.bots?.[version] || { equity: 0, signals_count: 0 };
  };

  // CRITICAL: Ensure 24h bot is always present
  if (!summary.bots) {
    summary.bots = {};
  }
  if (!summary.bots['24h']) {
    console.warn('⚠️ Dashboard: 24h bot missing, adding default');
    summary.bots['24h'] = {
      equity: 0,
      signals_count: 0,
      status: 'unknown'
    };
  }

  console.log('Dashboard render - summary.bots keys:', Object.keys(summary.bots || {}));
  console.log('Dashboard render - has 24h:', !!summary.bots['24h']);

  return (
    <div className="dashboard-summary">
      <div className="summary-card total-equity">
        <div className="summary-icon">💰</div>
        <div className="summary-content">
          <h3>Total Equity</h3>
          <p className="summary-value">{formatCurrency(summary.total_equity || 0)}</p>
        </div>
      </div>

      <div className="summary-card total-signals">
        <div className="summary-icon">📊</div>
        <div className="summary-content">
          <h3>Total Signals</h3>
          <p className="summary-value">{summary.total_signals || 0}</p>
        </div>
      </div>

      <div className="summary-card bot-5m">
        <div className="summary-icon">⚡</div>
        <div className="summary-content">
          <h3>5-Minute Bot</h3>
          <p className="summary-value">{formatCurrency(getBotData('5m').equity)}</p>
          <p className="summary-subtitle">{getBotData('5m').signals_count || 0} signals</p>
        </div>
      </div>

      <div className="summary-card bot-1h">
        <div className="summary-icon">🕐</div>
        <div className="summary-content">
          <h3>1-Hour Bot</h3>
          <p className="summary-value">{formatCurrency(getBotData('1h').equity)}</p>
          <p className="summary-subtitle">{getBotData('1h').signals_count || 0} signals</p>
        </div>
      </div>

      <div className="summary-card bot-12h">
        <div className="summary-icon">🕛</div>
        <div className="summary-content">
          <h3>12-Hour Bot</h3>
          <p className="summary-value">{formatCurrency(getBotData('12h').equity)}</p>
          <p className="summary-subtitle">{getBotData('12h').signals_count || 0} signals</p>
        </div>
      </div>

      <div className="summary-card bot-24h">
        <div className="summary-icon">🌙</div>
        <div className="summary-content">
          <h3>24-Hour Bot</h3>
          <p className="summary-value">{formatCurrency(getBotData('24h').equity)}</p>
          <p className="summary-subtitle">{getBotData('24h').signals_count || 0} signals</p>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

