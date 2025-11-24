import React, { useState, useEffect, useCallback } from 'react';
import { exportToCSV, exportToJSON } from '../utils/exportData';
import './ExecutionsTable.css';

// Use empty string for relative paths in production, localhost for dev
const API_BASE = process.env.REACT_APP_API_URL === '' ? '' : (process.env.REACT_APP_API_URL || 'http://localhost:8000');

const ExecutionsTable = ({ botVersion }) => {
  const [executions, setExecutions] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchExecutions = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/bots/${botVersion}/executions?limit=200`);
      const result = await response.json();
      
      if (result.data && result.data.length > 0) {
        // Use exact column names: ts_iso, side, qty, fill_price, etc.
        const formattedExecutions = result.data.map(item => ({
          timestamp: item.ts_iso || item.ts || item.timestamp || '',
          side: item.side || 'N/A',
          size: item.qty || item.size || 'N/A',
          price: item.fill_price || item.price || item.mid_price || 'N/A',
          notional: item.notional_usd || 'N/A',
          pnl: item.realized_pnl || item.unrealized_pnl || 'N/A',
          raw: item
        }));
        setExecutions(formattedExecutions);
      } else {
        setExecutions([]);
      }
      setLoading(false);
    } catch (error) {
      console.error('Error fetching executions:', error);
      setLoading(false);
      setExecutions([]);
    }
  }, [botVersion]);

  useEffect(() => {
    if (botVersion !== '5m') {
      setLoading(false);
      return;
    }
    fetchExecutions();
    const interval = setInterval(fetchExecutions, 10000);
    return () => clearInterval(interval);
  }, [botVersion, fetchExecutions]);

  const formatTimestamp = (ts) => {
    if (!ts) return 'N/A';
    try {
      const date = new Date(ts);
      if (!isNaN(date.getTime())) {
        return date.toLocaleString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        });
      }
    } catch {}
    return String(ts).substring(0, 16);
  };

  const formatPrice = (value) => {
    if (typeof value !== 'number' || isNaN(value)) return value;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  if (botVersion !== '5m' && botVersion !== '24h') {
    return (
      <div className="executions-table-container">
        <div className="no-data">Executions only available for 5-minute and 24-hour bots</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="executions-table-container">
        <div className="loading">Loading executions...</div>
      </div>
    );
  }

  if (executions.length === 0) {
    return (
      <div className="executions-table-container">
        <div className="no-data">No executions available</div>
      </div>
    );
  }

  const handleExportCSV = () => {
    if (executions.length === 0) {
      alert('No data to export');
      return;
    }
    exportToCSV(executions, `executions_${botVersion}`);
  };

  const handleExportJSON = () => {
    if (executions.length === 0) {
      alert('No data to export');
      return;
    }
    exportToJSON(executions, `executions_${botVersion}`);
  };

  return (
    <div className="executions-table-container">
      <div className="table-actions">
        <button onClick={handleExportCSV} className="export-button" title="Export as CSV">
          📥 CSV
        </button>
        <button onClick={handleExportJSON} className="export-button" title="Export as JSON">
          📥 JSON
        </button>
      </div>
      <div className="table-wrapper">
        <table className="executions-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Side</th>
              <th>Size</th>
              <th>Price</th>
              <th>Notional</th>
              <th>PnL</th>
            </tr>
          </thead>
          <tbody>
            {executions.slice().reverse().map((exec, idx) => (
              <tr key={idx}>
                <td className="timestamp-cell">{formatTimestamp(exec.timestamp)}</td>
                <td>
                  <span className={`side-badge ${String(exec.side).toLowerCase()}`}>
                    {String(exec.side).toUpperCase()}
                  </span>
                </td>
                <td className="numeric-cell">{typeof exec.size === 'number' ? exec.size.toFixed(4) : exec.size}</td>
                <td className="numeric-cell">{formatPrice(exec.price)}</td>
                <td className="numeric-cell">{typeof exec.notional === 'number' ? formatPrice(exec.notional) : exec.notional}</td>
                <td className={`numeric-cell ${typeof exec.pnl === 'number' && exec.pnl >= 0 ? 'positive' : 'negative'}`}>
                  {typeof exec.pnl === 'number' ? `$${exec.pnl.toFixed(2)}` : exec.pnl}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ExecutionsTable;
