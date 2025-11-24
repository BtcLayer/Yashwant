import React, { useState, useEffect, useCallback } from 'react';
import { exportToCSV, exportToJSON } from '../utils/exportData';
import './SignalsTable.css';

// Use empty string for relative paths in production, localhost for dev
const API_BASE = process.env.REACT_APP_API_URL === '' ? '' : (process.env.REACT_APP_API_URL || 'http://localhost:8000');

const SignalsTable = ({ botVersion }) => {
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchSignals = useCallback(async () => {
    try {
      setLoading(true);
      const url = `${API_BASE}/api/bots/${botVersion}/signals?limit=200`;
      console.log('Fetching signals from:', url);
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('Signals data result:', { version: result.version, count: result.count });
      
      if (result.data && result.data.length > 0) {
        // Use exact column names: ts_iso, S_top, S_bot, dir, alpha, etc.
        const formattedSignals = result.data.map(item => ({
          timestamp: item.ts_iso || item.ts || item.timestamp || '',
          signal: item.dir || item.S_top || item.decision || 'N/A',
          score: item.S_top || item.score || 'N/A',
          confidence: item.alpha || item.F_top_norm || item.confidence || 'N/A',
          price: item.close || item.price || 'N/A',
          volume: item.volume || 'N/A',
          raw: item
        }));
        setSignals(formattedSignals);
      } else {
        console.warn('No signals data in response:', result);
        setSignals([]);
      }
      setLoading(false);
    } catch (error) {
      console.error('Error fetching signals:', error);
      setLoading(false);
      setSignals([]);
    }
  }, [botVersion]);

  useEffect(() => {
    fetchSignals();
    const interval = setInterval(fetchSignals, 10000);
    return () => clearInterval(interval);
  }, [fetchSignals]);

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

  const getSignalColor = (signal) => {
    const s = String(signal || '').toLowerCase();
    if (s === '1' || s === 'buy' || s === 'long') return 'hsl(142 76% 36%)';
    if (s === '-1' || s === 'sell' || s === 'short') return 'hsl(0 84% 60%)';
    return 'hsl(var(--muted-foreground))';
  };

  const getSignalLabel = (signal) => {
    const s = String(signal || '');
    if (s === '1' || s === '1.0') return 'LONG';
    if (s === '-1' || s === '-1.0') return 'SHORT';
    if (s === '0' || s === '0.0') return 'NEUTRAL';
    return s.toUpperCase();
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

  if (loading) {
    return (
      <div className="signals-table-container">
        <div className="loading">Loading signals...</div>
      </div>
    );
  }

  if (signals.length === 0) {
    return (
      <div className="signals-table-container">
        <div className="no-data">
          <p>No signals available</p>
          <p className="no-data-hint" style={{ fontSize: '0.875rem', color: 'hsl(var(--muted-foreground))', marginTop: '0.5rem' }}>
            Signals will appear once the bot generates trading signals
          </p>
        </div>
      </div>
    );
  }

  const handleExportCSV = () => {
    if (signals.length === 0) {
      alert('No data to export');
      return;
    }
    exportToCSV(signals, `signals_${botVersion}`);
  };

  const handleExportJSON = () => {
    if (signals.length === 0) {
      alert('No data to export');
      return;
    }
    exportToJSON(signals, `signals_${botVersion}`);
  };

  return (
    <div className="signals-table-container">
      <div className="table-actions">
        <button onClick={handleExportCSV} className="export-button" title="Export as CSV">
          📥 CSV
        </button>
        <button onClick={handleExportJSON} className="export-button" title="Export as JSON">
          📥 JSON
        </button>
      </div>
      <div className="table-wrapper">
        <table className="signals-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Signal</th>
              <th>Score</th>
              <th>Price</th>
              <th>Volume</th>
            </tr>
          </thead>
          <tbody>
            {signals.slice().reverse().map((signal, idx) => (
              <tr key={idx}>
                <td className="timestamp-cell">{formatTimestamp(signal.timestamp)}</td>
                <td>
                  <span 
                    className="signal-badge"
                    style={{ color: getSignalColor(signal.signal) }}
                  >
                    {getSignalLabel(signal.signal)}
                  </span>
                </td>
                <td className="numeric-cell">{typeof signal.score === 'number' ? signal.score.toFixed(4) : signal.score}</td>
                <td className="numeric-cell">{formatPrice(signal.price)}</td>
                <td className="numeric-cell">{typeof signal.volume === 'number' ? signal.volume.toFixed(2) : signal.volume}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SignalsTable;
