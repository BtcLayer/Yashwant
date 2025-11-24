import React, { useState, useEffect, useCallback } from 'react';
import { exportToJSON } from '../utils/exportData';
import './HealthMetrics.css';

// Use empty string for relative paths in production, localhost for dev
const API_BASE = process.env.REACT_APP_API_URL === '' ? '' : (process.env.REACT_APP_API_URL || 'http://localhost:8000');

const HealthMetrics = ({ botVersion }) => {
  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchHealthMetrics = useCallback(async () => {
    try {
      setLoading(true);
      const url = `${API_BASE}/api/bots/${botVersion}/health?limit=10`;
      console.log('Fetching health metrics from:', url);
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('Health metrics result:', { 
        version: result.version, 
        count: result.count, 
        hasData: !!result.data,
        dataLength: result.data?.length || 0,
        fileExists: result.file_exists,
        firstItem: result.data?.[0]
      });
      
      if (result.data && Array.isArray(result.data) && result.data.length > 0) {
        console.log('Setting metrics:', result.data.length, 'items');
        console.log('First metric keys:', Object.keys(result.data[0]));
        console.log('First metric sample:', result.data[0]);
        setMetrics(result.data);
      } else {
        console.warn('No health metrics data in response:', result);
        setMetrics([]);
      }
      setLoading(false);
    } catch (error) {
      console.error('Error fetching health metrics:', error);
      setLoading(false);
      setMetrics([]);
    }
  }, [botVersion]);

  useEffect(() => {
    fetchHealthMetrics();
    const interval = setInterval(fetchHealthMetrics, 15000);
    return () => clearInterval(interval);
  }, [fetchHealthMetrics]);

  const getMetricValue = (metric, key) => {
    if (!metric || typeof metric !== 'object') return '-';
    
    // Try exact match first (allow 0 and empty string as valid values)
    if (metric.hasOwnProperty(key)) {
      const value = metric[key];
      // Only skip if explicitly null or undefined
      if (value !== null && value !== undefined) {
        return value;
      }
    }
    
    // Try case-insensitive
    const lowerKey = key.toLowerCase();
    for (const k in metric) {
      if (k.toLowerCase() === lowerKey) {
        const value = metric[k];
        if (value !== null && value !== undefined) {
          return value;
        }
      }
    }
    
    // Try common field name variations (backend should normalize, but handle edge cases)
    const fieldMappings = {
      'Sharpe_roll_1d': ['Sharpe_1w', 'sharpe_1w', 'Sharpe_roll_1d', 'sharpe_roll_1d'],
      'max_dd_to_date': ['max_DD_pct', 'max_dd_pct', 'max_dd_to_date', 'maxDrawdown', 'max_drawdown'],
      'ic_drift': ['ic_drift', 'icDrift', 'IC_drift']
    };
    
    if (fieldMappings[key]) {
      for (const altKey of fieldMappings[key]) {
        if (metric.hasOwnProperty(altKey)) {
          const value = metric[altKey];
          // Only skip if explicitly null or undefined (0 and empty string are valid)
          if (value !== null && value !== undefined) {
            return value;
          }
        }
        // Also try case-insensitive
        for (const k in metric) {
          if (k.toLowerCase() === altKey.toLowerCase()) {
            const value = metric[k];
            if (value !== null && value !== undefined) {
              return value;
            }
          }
        }
      }
    }
    
    // Try variations (remove underscores, spaces, etc.)
    const keyVariations = [
      key.replace(/_/g, ''),
      key.replace(/_/g, ' '),
      key.toLowerCase().replace(/_/g, ''),
      key.toLowerCase().replace(/_/g, ' '),
      key.replace(/_/g, '-'),
      key.toLowerCase().replace(/_/g, '-')
    ];
    
    for (const variant of keyVariations) {
      if (metric.hasOwnProperty(variant)) {
        const value = metric[variant];
        if (value !== null && value !== undefined) {
          return value;
        }
      }
      // Also try case-insensitive match for variants
      for (const k in metric) {
        if (k.toLowerCase() === variant.toLowerCase()) {
          const value = metric[k];
          if (value !== null && value !== undefined) {
            return value;
          }
        }
      }
    }
    
    // Key not found - return null (formatValue will handle it)
    return null;
  };

  const formatValue = (value) => {
    if (value === null || value === undefined || value === '') return '-';
    // Handle 0 as a valid value
    if (value === 0) return '0.0000';
    const num = parseFloat(value);
    if (isNaN(num)) return String(value);
    return num.toFixed(4);
  };

  const getStatusColor = (value, type) => {
    const v = parseFloat(value);
    if (isNaN(v)) return 'hsl(var(--muted-foreground))';
    
    if (type === 'sharpe') {
      if (v > 1) return 'hsl(142 76% 36%)';
      if (v > 0) return 'hsl(38 92% 50%)';
      return 'hsl(0 84% 60%)';
    }
    if (type === 'drawdown') {
      if (v > -0.02) return 'hsl(142 76% 36%)';
      if (v > -0.03) return 'hsl(38 92% 50%)';
      return 'hsl(0 84% 60%)';
    }
    return 'hsl(var(--dark-foreground))';
  };

  if (loading) {
    return (
      <div className="health-metrics-container">
        <div className="loading">Loading health metrics...</div>
      </div>
    );
  }

  if (metrics.length === 0) {
    return (
      <div className="health-metrics-container">
        <div className="no-data">
          <p>No health metrics available</p>
          <p className="no-data-hint" style={{ fontSize: '0.875rem', color: 'hsl(var(--muted-foreground))', marginTop: '0.5rem' }}>
            Health metrics will appear once the bot generates data
          </p>
        </div>
      </div>
    );
  }

  const latest = metrics[metrics.length - 1];

  const handleExport = () => {
    if (metrics.length === 0) {
      alert('No data to export');
      return;
    }
    exportToJSON(metrics, `health_metrics_${botVersion}`);
  };

  // Metrics are available if we have data

  return (
    <div className="health-metrics-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div style={{ fontSize: '0.75rem', color: 'hsl(var(--muted-foreground))' }}>
          {metrics.length > 0 ? `Showing ${metrics.length} metric${metrics.length > 1 ? 's' : ''}` : 'No metrics available'}
        </div>
        {metrics.length > 0 && (
          <button onClick={handleExport} className="export-button" title="Export as JSON">
            📥 Export JSON
          </button>
        )}
      </div>
      {metrics.length > 0 ? (
        <>
          <div className="metrics-grid">
            <div className="metric-item">
              <div className="metric-label">Sharpe Ratio (1d)</div>
              <div 
                className="metric-value"
                style={{ color: getStatusColor(getMetricValue(latest, 'Sharpe_roll_1d'), 'sharpe') }}
              >
                {formatValue(getMetricValue(latest, 'Sharpe_roll_1d'))}
              </div>
            </div>
            <div className="metric-item">
              <div className="metric-label">Max Drawdown</div>
              <div 
                className="metric-value"
                style={{ color: getStatusColor(getMetricValue(latest, 'max_dd_to_date'), 'drawdown') }}
              >
                {formatValue(getMetricValue(latest, 'max_dd_to_date'))}
              </div>
            </div>
            <div className="metric-item">
              <div className="metric-label">IC Drift</div>
              <div className="metric-value">
                {formatValue(getMetricValue(latest, 'ic_drift'))}
              </div>
            </div>
          {getMetricValue(latest, 'Sharpe_roll_1w') !== '-' && (
            <div className="metric-item">
              <div className="metric-label">Sharpe Ratio (1w)</div>
              <div 
                className="metric-value"
                style={{ color: getStatusColor(getMetricValue(latest, 'Sharpe_roll_1w'), 'sharpe') }}
              >
                {formatValue(getMetricValue(latest, 'Sharpe_roll_1w'))}
              </div>
            </div>
          )}
          {getMetricValue(latest, 'Sortino_1w') !== '-' && (
            <div className="metric-item">
              <div className="metric-label">Sortino (1w)</div>
              <div className="metric-value">
                {formatValue(getMetricValue(latest, 'Sortino_1w'))}
              </div>
            </div>
          )}
          {getMetricValue(latest, 'hit_rate_w') !== '-' && (
            <div className="metric-item">
              <div className="metric-label">Hit Rate (1w)</div>
              <div className="metric-value">
                {formatValue(getMetricValue(latest, 'hit_rate_w'))}
              </div>
            </div>
          )}
          <div className="metric-item">
            <div className="metric-label">Last Update</div>
            <div className="metric-value small">
              {latest.ts_iso ? new Date(latest.ts_iso).toLocaleString() : 
               latest.ts ? new Date(latest.ts).toLocaleString() : '-'}
            </div>
          </div>
          </div>
          {/* Debug: Show all available keys */}
          <details style={{ marginTop: '1rem', padding: '1rem', background: 'hsl(var(--secondary))', borderRadius: 'calc(var(--radius) - 2px)', fontSize: '0.75rem' }}>
            <summary style={{ cursor: 'pointer', color: 'hsl(var(--muted-foreground))', fontWeight: 500 }}>
              🔍 Debug: Show all available fields ({Object.keys(latest).length} fields)
            </summary>
            <div style={{ marginTop: '0.5rem', fontFamily: 'monospace' }}>
              {Object.keys(latest).map(key => (
                <div key={key} style={{ padding: '0.25rem 0', borderBottom: '1px solid hsl(var(--border))' }}>
                  <strong>{key}:</strong> {String(latest[key]).substring(0, 100)}
                </div>
              ))}
            </div>
          </details>
        </>
      ) : (
        <div className="no-data">
          <p>No health metrics available for {botVersion.toUpperCase()} bot</p>
          <p style={{ fontSize: '0.75rem', marginTop: '0.5rem', color: 'hsl(var(--muted-foreground))' }}>
            Health metrics are generated during bot execution
          </p>
        </div>
      )}
    </div>
  );
};

export default HealthMetrics;
