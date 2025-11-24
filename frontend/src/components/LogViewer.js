import React, { useState, useEffect, useCallback } from 'react';
import { exportToCSV, exportToJSON } from '../utils/exportData';
import './LogViewer.css';

// Use empty string for relative paths in production, localhost for dev
const API_BASE = process.env.REACT_APP_API_URL === '' ? '' : (process.env.REACT_APP_API_URL || 'http://localhost:8000');

const LogViewer = ({ botVersion = null, showBotFilter = true }) => {
  const [logTypes, setLogTypes] = useState([]);
  const [selectedLogType, setSelectedLogType] = useState('');
  const [availableDates, setAvailableDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [limit, setLimit] = useState(50);
  const [expandedLog, setExpandedLog] = useState(null);
  const [selectedBotFilter, setSelectedBotFilter] = useState(botVersion || 'all');

  const fetchLogTypes = useCallback(async () => {
    try {
      // If botVersion prop is provided, use it; otherwise use selectedBotFilter
      const filterBot = botVersion || (selectedBotFilter !== 'all' ? selectedBotFilter : null);
      const url = filterBot 
        ? `${API_BASE}/api/logs/types?bot_version=${filterBot}`
        : `${API_BASE}/api/logs/types`;
      const response = await fetch(url);
      const result = await response.json();
      setLogTypes(result.log_types || []);
      if (result.log_types && result.log_types.length > 0) {
        setSelectedLogType(result.log_types[0]);
      }
    } catch (error) {
      console.error('Error fetching log types:', error);
    }
  }, [botVersion, selectedBotFilter]);

  const fetchAvailableDates = useCallback(async () => {
    try {
      // If botVersion prop is provided, use it; otherwise use selectedBotFilter
      const filterBot = botVersion || (selectedBotFilter !== 'all' ? selectedBotFilter : null);
      const url = filterBot
        ? `${API_BASE}/api/logs/${selectedLogType}/dates?bot_version=${filterBot}`
        : `${API_BASE}/api/logs/${selectedLogType}/dates`;
      const response = await fetch(url);
      const result = await response.json();
      setAvailableDates(result.dates || []);
      if (result.dates && result.dates.length > 0) {
        setSelectedDate(result.dates[0]);
      } else {
        // If no dates, set empty string to allow fetching logs without date filter
        setSelectedDate('');
      }
    } catch (error) {
      console.error('Error fetching dates:', error);
      setAvailableDates([]);
      setSelectedDate('');
    }
  }, [selectedLogType, botVersion, selectedBotFilter]);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      // If botVersion prop is provided, use it; otherwise use selectedBotFilter
      const filterBot = botVersion || (selectedBotFilter !== 'all' ? selectedBotFilter : null);
      const url = filterBot
        ? `${API_BASE}/api/logs/${selectedLogType}?date=${selectedDate}&limit=${limit}&bot_version=${filterBot}`
        : `${API_BASE}/api/logs/${selectedLogType}?date=${selectedDate}&limit=${limit}`;
      console.log('Fetching logs from:', url);
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('Logs result:', { 
        log_type: result.log_type, 
        count: result.count, 
        hasData: !!result.data,
        dataLength: result.data?.length || 0,
        firstLog: result.data?.[0] 
      });
      
      if (result.data && Array.isArray(result.data) && result.data.length > 0) {
        setLogs(result.data);
      } else {
        console.warn('No logs data in response:', result);
        setLogs([]);
      }
    } catch (error) {
      console.error('Error fetching logs:', error);
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [selectedLogType, selectedDate, limit, botVersion, selectedBotFilter]);

  useEffect(() => {
    fetchLogTypes();
  }, [fetchLogTypes]);

  useEffect(() => {
    if (selectedLogType) {
      fetchAvailableDates();
    }
  }, [selectedLogType, fetchAvailableDates, selectedBotFilter]);

  // Update selectedBotFilter when botVersion prop changes
  useEffect(() => {
    if (botVersion) {
      setSelectedBotFilter(botVersion);
    }
  }, [botVersion]);

  useEffect(() => {
    if (selectedLogType) {
      // Fetch logs even if no date is selected (backend will use latest date)
      fetchLogs();
    }
  }, [selectedLogType, selectedDate, limit, fetchLogs]);

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    try {
      const date = new Date(timestamp);
      if (isNaN(date.getTime())) {
        return String(timestamp).substring(0, 19);
      }
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return String(timestamp).substring(0, 19);
    }
  };

  const getLogPreview = (log) => {
    // Try to get meaningful preview from log
    const parts = [];
    
    if (log.sanitized) {
      const sanitized = log.sanitized;
      if (sanitized.symbol) parts.push(`Symbol: ${sanitized.symbol}`);
      if (sanitized.asset) parts.push(`Asset: ${sanitized.asset}`);
      if (sanitized.preds) parts.push('Ensemble Predictions');
      if (sanitized.exec) parts.push('Execution Data');
      if (sanitized.risk) parts.push('Risk State');
      if (sanitized.metrics) parts.push('Health Metrics');
      if (sanitized.decision) parts.push(`Decision: ${sanitized.decision.dir || sanitized.decision}`);
    }
    
    if (log.bar_id) parts.push(`Bar ID: ${log.bar_id}`);
    if (log.event) parts.push(`Event: ${log.event}`);
    if (log.chosen) parts.push(`Chosen: ${log.chosen}`);
    if (log.dir) parts.push(`Direction: ${log.dir}`);
    if (log.pred_cal_bps !== undefined) parts.push(`Pred: ${log.pred_cal_bps} bps`);
    if (log.fill_px) parts.push(`Fill: $${log.fill_px}`);
    if (log.fill_qty) parts.push(`Qty: ${log.fill_qty}`);
    if (log.position_after !== undefined) parts.push(`Position: ${log.position_after}`);
    if (log.equity_value) parts.push(`Equity: $${log.equity_value}`);
    
    // Get first meaningful key-value pair if nothing found
    if (parts.length === 0) {
      const keys = Object.keys(log).filter(k => 
        k !== 'ts_iso' && k !== 'ts' && k !== 'timestamp' && 
        k !== 'sanitized' && k !== 'symbol' && k !== 'asset' &&
        typeof log[k] !== 'object' && log[k] !== null && log[k] !== undefined
      );
      if (keys.length > 0) {
        const key = keys[0];
        const value = log[key];
        parts.push(`${key}: ${String(value).substring(0, 40)}`);
      }
    }
    
    return parts.length > 0 ? parts.join(' • ') : 'Log Entry';
  };

  const formatJson = (obj) => {
    return JSON.stringify(obj, null, 2);
  };

  const getLogTypeIcon = (type) => {
    const icons = {
      'ensemble_log': '🎯',
      'execution_log': '⚡',
      'calibration_log': '⚙️',
      'kpi_scorecard': '📊',
      'market_ingest_log': '📈',
      'overlay_status': '🔀',
      'pnl_equity_log': '💰',
      'sizing_risk_log': '🛡️',
      'hyperliquid_fills': '🔄',
      'signals': '📡',
      'health': '💚',
      'costs': '💸',
      'repro': '🔬',
      'feature_log': '🔧',
      'order_intent': '📋'
    };
    return icons[type] || '📝';
  };
  
  const formatLogTypeName = (type) => {
    return type
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  };

  // Emitter information - map log types to their emitter methods
  const emitterInfo = {
    'ensemble': { method: 'emit_ensemble', description: 'Model ensemble predictions', sink: 'emitter+llm' },
    'signals': { method: 'emit_signals', description: 'Trading signals', sink: 'emitter' },
    'execution': { method: 'emit_execution', description: 'Trade executions', sink: 'emitter+llm' },
    'execution_log': { method: 'emit_execution', description: 'Trade executions (LLM)', sink: 'llm' },
    'health': { method: 'emit_health', description: 'Health metrics', sink: 'emitter' },
    'repro': { method: 'emit_repro', description: 'Reproducibility logs', sink: 'emitter' },
    'costs': { method: 'emit_costs', description: 'Trading costs', sink: 'emitter+llm' },
    'order_intent': { method: 'emit_order_intent', description: 'Order intentions', sink: 'emitter' },
    'feature_log': { method: 'emit_feature_log', description: 'Feature logging', sink: 'emitter' },
    'calibration': { method: 'emit_calibration', description: 'Calibration logs', sink: 'emitter' },
    'calibration_log': { method: 'emit_calibration', description: 'Calibration logs (LLM)', sink: 'llm' },
    'hyperliquid_fill': { method: 'emit_hyperliquid_fill', description: 'Hyperliquid fills', sink: 'emitter+llm' },
    'hyperliquid_fills': { method: 'emit_hyperliquid_fill', description: 'Hyperliquid fills (LLM)', sink: 'llm' },
    'equity': { method: 'emit_equity', description: 'Equity/PnL tracking', sink: 'llm' },
    'pnl_equity_log': { method: 'emit_equity', description: 'Equity/PnL tracking (LLM)', sink: 'llm' },
    'overlay_status': { method: 'emit_overlay_status', description: 'Overlay status', sink: 'llm' },
    'alerts': { method: 'emit_alert', description: 'Alert logs', sink: 'llm' },
    'ensemble_log': { method: 'emit_ensemble', description: 'Model ensemble predictions (LLM)', sink: 'llm' },
  };

  const getEmitterInfo = (logType) => {
    return emitterInfo[logType] || { method: 'N/A', description: 'Unknown emitter', sink: 'N/A' };
  };

  return (
    <div className="log-viewer">
      <div className="log-viewer-header">
        <h3>📋 Logs & Emitters Viewer</h3>
        <p className="log-viewer-subtitle">
          {botVersion 
            ? `View logs and emitter data for ${botVersion === '5m' ? '5-Minute' : botVersion === '1h' ? '1-Hour' : botVersion === '12h' ? '12-Hour' : '24-Hour'} bot`
            : 'View detailed logging and emitter data'}
        </p>
      </div>

      {/* Emitter Information Section */}
      {selectedLogType && (
        <div className="emitter-info-section" style={{ 
          marginBottom: '1.5rem', 
          padding: '1rem', 
          backgroundColor: 'hsl(var(--muted))', 
          borderRadius: '8px',
          border: '1px solid hsl(var(--border))'
        }}>
          <h4 style={{ margin: '0 0 0.75rem 0', fontSize: '1rem', fontWeight: '600' }}>
            🔧 Emitter Information
          </h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', fontSize: '0.875rem' }}>
            <div>
              <strong>Emitter Method:</strong> <code style={{ backgroundColor: 'hsl(var(--background))', padding: '0.25rem 0.5rem', borderRadius: '4px' }}>{getEmitterInfo(selectedLogType).method}</code>
            </div>
            <div>
              <strong>Description:</strong> {getEmitterInfo(selectedLogType).description}
            </div>
            <div>
              <strong>Sink:</strong> <span style={{ 
                backgroundColor: getEmitterInfo(selectedLogType).sink.includes('emitter') ? 'hsl(142, 76%, 36%)' : 'hsl(217, 91%, 60%)',
                color: 'white',
                padding: '0.25rem 0.5rem',
                borderRadius: '4px',
                fontSize: '0.75rem',
                fontWeight: '500'
              }}>
                {getEmitterInfo(selectedLogType).sink}
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="log-controls">
        {showBotFilter && !botVersion && (
          <div className="control-group">
            <label>Bot Version</label>
            <select 
              value={selectedBotFilter} 
              onChange={(e) => setSelectedBotFilter(e.target.value)}
              className="log-select"
            >
              <option value="all">All Bots</option>
              <option value="5m">⚡ 5-Minute</option>
              <option value="1h">🕐 1-Hour</option>
              <option value="12h">🕛 12-Hour</option>
              <option value="24h">🌙 24-Hour</option>
            </select>
          </div>
        )}
        <div className="control-group">
          <label>Log Type</label>
          <select 
            value={selectedLogType} 
            onChange={(e) => setSelectedLogType(e.target.value)}
            className="log-select"
          >
            {logTypes.map(type => (
              <option key={type} value={type}>
                {getLogTypeIcon(type)} {formatLogTypeName(type)}
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label>Date</label>
          <select 
            value={selectedDate} 
            onChange={(e) => setSelectedDate(e.target.value)}
            className="log-select"
            disabled={!selectedLogType}
          >
            {availableDates.map(date => (
              <option key={date} value={date}>{date}</option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label>Limit</label>
          <select 
            value={limit} 
            onChange={(e) => setLimit(Number(e.target.value))}
            className="log-select"
          >
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
            <option value={500}>500</option>
          </select>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-end' }}>
          <button 
            onClick={() => exportToCSV(logs, `${selectedLogType}_${selectedDate}`)} 
            className="export-button" 
            disabled={loading || logs.length === 0}
            title="Export as CSV"
          >
            📥 CSV
          </button>
          <button 
            onClick={() => exportToJSON(logs, `${selectedLogType}_${selectedDate}`)} 
            className="export-button" 
            disabled={loading || logs.length === 0}
            title="Export as JSON"
          >
            📥 JSON
          </button>
          <button onClick={fetchLogs} className="refresh-button" disabled={loading}>
            {loading ? '⏳ Loading...' : '🔄 Refresh'}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading logs...</p>
        </div>
      ) : logs.length === 0 ? (
        <div className="no-data">
          <div className="no-data-icon">📭</div>
          <p>No logs available for {selectedLogType}{selectedDate ? ` on ${selectedDate}` : ''}</p>
          <p style={{ fontSize: '0.9rem', opacity: 0.7, marginTop: '0.5rem' }}>
            Make sure the trading bots are running and generating logs.
          </p>
        </div>
      ) : (
        <div className="logs-container">
          <div className="logs-header">
            <span>Showing {logs.length} log entries</span>
            <span className="log-type-badge">{selectedLogType}</span>
            {selectedLogType && (
              <span style={{ 
                fontSize: '0.75rem', 
                opacity: 0.7,
                marginLeft: '0.5rem'
              }}>
                via {getEmitterInfo(selectedLogType).method}
              </span>
            )}
          </div>
          <div className="logs-list">
            {logs.slice().reverse().map((log, index) => {
              const logIndex = logs.length - index;
              const timestamp = log.ts_iso || log.ts || log.timestamp || log.exec_time_ist;
              const symbol = log.symbol || log.asset || (log.sanitized && (log.sanitized.symbol || log.sanitized.asset));
              const preview = getLogPreview(log);
              
              return (
                <div key={index} className="log-entry">
                  <div 
                    className="log-entry-header"
                    onClick={() => setExpandedLog(expandedLog === index ? null : index)}
                  >
                    <div className="log-entry-info">
                      <span className="log-index">#{logIndex}</span>
                      <span className="log-timestamp">
                        {formatTimestamp(timestamp)}
                      </span>
                      {symbol && (
                        <span className="log-symbol">{symbol}</span>
                      )}
                    </div>
                    <div className="log-preview-section">
                      <span className="log-preview">{preview}</span>
                    </div>
                    <div className="log-expand-icon">
                      {expandedLog === index ? '▼' : '▶'}
                    </div>
                  </div>
                  {expandedLog === index && (
                    <div className="log-entry-content">
                      <pre className="log-json">{formatJson(log)}</pre>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default LogViewer;

