import React, { useState, useEffect, useCallback } from 'react';
import { AreaChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceArea } from 'recharts';
import { exportToCSV, exportToJSON } from '../utils/exportData';
import './EquityChart.css';

// Use empty string for relative paths in production, localhost for dev
const API_BASE = process.env.REACT_APP_API_URL === '' ? '' : (process.env.REACT_APP_API_URL || 'http://localhost:8000');

const EquityChart = ({ botVersion }) => {
  const [data, setData] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchEquityData = useCallback(async () => {
    try {
      setError(null);
      setLoading(true);
      const url = `${API_BASE}/api/bots/${botVersion}/equity?limit=200`;
      console.log('Fetching enhanced equity data from:', url);
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('Enhanced equity data result:', {
        version: result.version,
        count: result.count,
        hasMetrics: !!result.metrics,
        metricsKeys: result.metrics ? Object.keys(result.metrics) : []
      });

      if (result.data && result.data.length > 0) {
        const formattedData = result.data.map((item, index) => {
          const timestamp = item.ts_iso || item.ts || '';
          const equity = parseFloat(item.equity || 0);
          const realized = parseFloat(item.realized || 0);
          const unrealized = parseFloat(item.unrealized || 0);
          const totalPnL = realized + unrealized;

          // Format timestamp
          let displayTime = '';
          if (timestamp) {
            try {
              const date = new Date(timestamp);
              if (!isNaN(date.getTime())) {
                displayTime = date.toLocaleString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                });
              } else {
                displayTime = String(timestamp).substring(0, 16);
              }
            } catch {
              displayTime = String(timestamp).substring(0, 16);
            }
          } else {
            displayTime = `#${index + 1}`;
          }

          // Build data point with all available metrics
          const dataPoint = {
            time: displayTime,
            equity: equity > 0 ? equity : null,
            pnl: totalPnL,
            realized: realized,
            unrealized: unrealized,
            drawdown: parseFloat(item.drawdown_pct || 0),
            rawTime: timestamp
          };

          // Add rolling metrics if available
          if (item.sharpe_7d !== undefined) dataPoint.sharpe_7d = parseFloat(item.sharpe_7d);
          if (item.sharpe_30d !== undefined) dataPoint.sharpe_30d = parseFloat(item.sharpe_30d);
          if (item.volatility_7d !== undefined) dataPoint.volatility_7d = parseFloat(item.volatility_7d);
          if (item.volatility_30d !== undefined) dataPoint.volatility_30d = parseFloat(item.volatility_30d);
          if (item.returns_7d !== undefined) dataPoint.returns_7d = parseFloat(item.returns_7d);
          if (item.returns_30d !== undefined) dataPoint.returns_30d = parseFloat(item.returns_30d);

          return dataPoint;
        }).filter(item => item.equity !== null && !isNaN(item.equity));

        if (formattedData.length > 0) {
          setData(formattedData);
          setMetrics(result.metrics || {});
        } else {
          setError('No valid equity data found');
          setData([]);
          setMetrics({});
        }
      } else {
        console.warn('No equity data in response:', result);
        setError('No equity data available');
        setData([]);
        setMetrics({});
      }
      setLoading(false);
    } catch (error) {
      console.error('Error fetching equity data:', error);
      setError(`Failed to load equity data: ${error.message}`);
      setData([]);
      setMetrics({});
      setLoading(false);
    }
  }, [botVersion]);

  useEffect(() => {
    fetchEquityData();
    const interval = setInterval(fetchEquityData, 15000); // Increased to 15s to reduce load
    return () => clearInterval(interval);
  }, [fetchEquityData]);

  const formatCurrency = (value) => {
    if (value === null || isNaN(value)) return '$0.00';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const formatPercentage = (value) => {
    if (value === null || isNaN(value)) return '0.00%';
    return `${value.toFixed(2)}%`;
  };

  const formatRatio = (value) => {
    if (value === null || isNaN(value)) return '0.00';
    return value.toFixed(2);
  };

  const getTooltipValue = (value, dataKey) => {
    if (value === null || isNaN(value)) return 'N/A';

    if (dataKey.includes('pct') || dataKey.includes('drawdown') || dataKey.includes('returns')) {
      return formatPercentage(value);
    } else if (dataKey.includes('sharpe') || dataKey.includes('ratio') || dataKey.includes('correlation')) {
      return formatRatio(value);
    } else if (dataKey.includes('volatility')) {
      return formatPercentage(value);
    } else {
      return formatCurrency(value);
    }
  };

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="chart-tooltip">
          <div className="tooltip-header">{label}</div>
          {payload.map((entry, index) => (
            <div key={index} className="tooltip-item" style={{ color: entry.color }}>
              <span className="tooltip-label">{entry.name}:</span>
              <span className="tooltip-value">{getTooltipValue(entry.value, entry.dataKey)}</span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  // Calculate drawdown periods for visualization
  const getDrawdownPeriods = () => {
    const periods = [];
    let inDrawdown = false;
    let startIndex = -1;

    data.forEach((point, index) => {
      const isInDrawdown = point.drawdown < -0.01; // More than 1% drawdown

      if (isInDrawdown && !inDrawdown) {
        // Start of drawdown period
        inDrawdown = true;
        startIndex = index;
      } else if (!isInDrawdown && inDrawdown) {
        // End of drawdown period
        inDrawdown = false;
        if (startIndex >= 0) {
          periods.push({
            x1: data[startIndex].time,
            x2: data[index - 1].time,
            fill: 'rgba(239, 68, 68, 0.1)' // Light red background
          });
        }
        startIndex = -1;
      }
    });

    // Handle ongoing drawdown
    if (inDrawdown && startIndex >= 0) {
      periods.push({
        x1: data[startIndex].time,
        x2: data[data.length - 1].time,
        fill: 'rgba(239, 68, 68, 0.1)'
      });
    }

    return periods;
  };

  if (loading) {
    return (
      <div className="equity-chart">
        <div className="chart-header">
          <h3>Enhanced Equity Analytics</h3>
          <p className="chart-subtitle">{botVersion.toUpperCase()} Bot</p>
        </div>
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading comprehensive analytics...</p>
        </div>
      </div>
    );
  }

  if (error || data.length === 0) {
    return (
      <div className="equity-chart">
        <div className="chart-header">
          <h3>Enhanced Equity Analytics</h3>
          <p className="chart-subtitle">{botVersion.toUpperCase()} Bot</p>
        </div>
        <div className="error-state">
          <p>{error || 'No equity data available'}</p>
          <p className="no-data-hint" style={{ fontSize: '0.875rem', color: 'hsl(var(--muted-foreground))', marginTop: '0.5rem' }}>
            Equity data will appear once the bot starts trading
          </p>
          <button onClick={fetchEquityData} className="retry-button">Retry</button>
        </div>
      </div>
    );
  }

  const latestEquity = data[data.length - 1]?.equity || 0;
  const initialEquity = data[0]?.equity || 0;
  const totalReturn = latestEquity - initialEquity;
  const returnPercent = initialEquity > 0 ? ((totalReturn / initialEquity) * 100) : 0;

  const handleExportCSV = () => {
    if (data.length === 0) {
      alert('No data to export');
      return;
    }
    exportToCSV(data, `enhanced_equity_${botVersion}`);
  };

  const handleExportJSON = () => {
    if (data.length === 0) {
      alert('No data to export');
      return;
    }
    exportToJSON(data, `enhanced_equity_${botVersion}`);
  };

  const drawdownPeriods = getDrawdownPeriods();

  return (
    <div className="equity-chart">
      <div className="chart-header">
        <div>
          <h3>Enhanced Equity Analytics</h3>
          <p className="chart-subtitle">{botVersion.toUpperCase()} Bot</p>
        </div>
        <div className="chart-actions">
          <button onClick={handleExportCSV} className="export-button" title="Export as CSV">
            📥 CSV
          </button>
          <button onClick={handleExportJSON} className="export-button" title="Export as JSON">
            📥 JSON
          </button>
        </div>
      </div>

      {/* Metrics Summary - Displayed at top for better visibility */}
      <div className="metrics-summary">
        <div className="metrics-grid">
          <div className="metric-card">
            <span className="metric-label">Current Equity</span>
            <span className="metric-value">{formatCurrency(latestEquity)}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Total Return</span>
            <span className={`metric-value ${totalReturn >= 0 ? 'positive' : 'negative'}`}>
              {formatCurrency(totalReturn)} ({formatPercentage(returnPercent)})
            </span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Sharpe Ratio</span>
            <span className="metric-value">{formatRatio(metrics.sharpe_ratio)}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Win Rate</span>
            <span className="metric-value">{formatPercentage((metrics.win_rate || 0) * 100)}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Max Drawdown</span>
            <span className="metric-value negative">{formatPercentage(metrics.max_drawdown_pct)}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Profit Factor</span>
            <span className="metric-value">{formatRatio(metrics.profit_factor)}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Volatility</span>
            <span className="metric-value">{formatPercentage(metrics.volatility)}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">BTC Correlation</span>
            <span className="metric-value">{formatRatio(metrics.btc_correlation)}</span>
          </div>
        </div>
      </div>

      <div className="chart-container">
        <ResponsiveContainer width="100%" height={500}>
          <AreaChart data={data} margin={{ top: 20, right: 80, left: 20, bottom: 80 }}>
            <defs>
              <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
              </linearGradient>
            </defs>

            {/* Drawdown background areas */}
            {drawdownPeriods.map((period, index) => (
              <ReferenceArea
                key={index}
                x1={period.x1}
                x2={period.x2}
                fill={period.fill}
                fillOpacity={0.3}
              />
            ))}

            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
            <XAxis
              dataKey="time"
              stroke="hsl(var(--muted-foreground))"
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
              angle={-45}
              textAnchor="end"
              height={80}
              interval="preserveStartEnd"
            />

            {/* Primary Y-axis for Equity */}
            <YAxis
              yAxisId="equity"
              orientation="left"
              stroke="hsl(var(--muted-foreground))"
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
              label={{ value: 'Equity ($)', angle: -90, position: 'insideLeft', fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
              tickFormatter={(value) => `$${value.toLocaleString()}`}
            />

            {/* Secondary Y-axis for PnL */}
            <YAxis
              yAxisId="pnl"
              orientation="right"
              stroke="#10b981"
              tick={{ fill: '#10b981', fontSize: 11 }}
              label={{ value: 'PnL ($)', angle: 90, position: 'insideRight', fill: '#10b981', fontSize: 12 }}
              tickFormatter={(value) => `$${value.toLocaleString()}`}
            />

            {/* Tertiary Y-axis for percentages/ratios */}
              <YAxis
                yAxisId="secondary"
                orientation="right"
                stroke="#6366f1"
                tick={{ fill: '#6366f1', fontSize: 11 }}
                label={{ value: '% / Ratio', angle: 90, position: 'outside', fill: '#6366f1', fontSize: 12 }}
                tickFormatter={(value) => `${value.toFixed(1)}`}
              />

            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: '12px' }} />

            {/* Core Equity Chart */}
              <Area
                yAxisId="equity"
                type="monotone"
                dataKey="equity"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                fill="url(#equityGradient)"
                name="Equity"
                dot={false}
                activeDot={{ r: 4, fill: 'hsl(var(--primary))' }}
              />

            {/* PnL Lines */}
              <Line
                yAxisId="pnl"
                type="monotone"
                dataKey="realized"
                stroke="#059669"
                strokeWidth={2}
                name="Realized PnL"
                dot={false}
                connectNulls={false}
              />

              <Line
                yAxisId="pnl"
                type="monotone"
                dataKey="unrealized"
                stroke="#dc2626"
                strokeWidth={2}
                name="Unrealized PnL"
                dot={false}
                connectNulls={false}
              />

            {/* Drawdown Area */}
              <Area
                yAxisId="secondary"
                type="monotone"
                dataKey="drawdown"
                stroke="#ef4444"
                strokeWidth={1}
                fill="url(#drawdownGradient)"
                name="Drawdown %"
                dot={false}
              />

            {/* Sharpe Ratio Line */}
              <Line
                yAxisId="secondary"
                type="monotone"
                dataKey="sharpe_7d"
                stroke="#f59e0b"
                strokeWidth={2}
                name="Sharpe Ratio (7d)"
                dot={false}
                connectNulls={false}
              />

            {/* Volatility Lines */}
                <Line
                  yAxisId="secondary"
                  type="monotone"
                  dataKey="volatility_7d"
                  stroke="#8b5cf6"
                  strokeWidth={1}
                  strokeDasharray="5 5"
                  name="Volatility (7d)"
                  dot={false}
                  connectNulls={false}
                />
                <Line
                  yAxisId="secondary"
                  type="monotone"
                  dataKey="volatility_30d"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  name="Volatility (30d)"
                  dot={false}
                  connectNulls={false}
                />

            {/* Rolling Returns */}
                <Line
                  yAxisId="secondary"
                  type="monotone"
                  dataKey="returns_7d"
                  stroke="#06b6d4"
                  strokeWidth={1}
                  strokeDasharray="3 3"
                  name="Returns (7d)"
                  dot={false}
                  connectNulls={false}
                />
                <Line
                  yAxisId="secondary"
                  type="monotone"
                  dataKey="returns_30d"
                  stroke="#06b6d4"
                  strokeWidth={2}
                  name="Returns (30d)"
                  dot={false}
                  connectNulls={false}
                />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default EquityChart;
