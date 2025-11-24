import React from 'react';
import './BotStatus.css';

const BotStatus = ({ bots, selectedBot, onSelectBot, loading }) => {
  const getStatusColor = (status) => {
    switch (status) {
      case 'running':
        return '#43e97b';
      case 'stopped':
        return '#f5576c';
      default:
        return '#888';
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value || 0);
  };

  if (loading) {
    return (
      <div className="bot-status">
        <h2>Bot Status</h2>
        <div className="loading">Loading...</div>
      </div>
    );
  }

  // Debug: Log what bots we have
  console.log('BotStatus render - bots prop:', bots);
  console.log('BotStatus render - available bot keys:', Object.keys(bots || {}));
  
  // Always render all 4 bots regardless of API response
  // CRITICAL: Ensure 24h bot is always in the list
  const botVersions = ['5m', '1h', '12h', '24h'];
  
  // Force ensure all bots have default values
  const normalizedBots = {};
  botVersions.forEach(version => {
    normalizedBots[version] = bots && bots[version] ? bots[version] : {
      equity: 0,
      signals_count: 0,
      status: 'unknown',
      has_data: false
    };
  });
  
  console.log('BotStatus - normalized bots:', normalizedBots);
  console.log('BotStatus - 24h bot exists:', !!normalizedBots['24h']);
  
  return (
    <div className="bot-status">
      <h2>Bot Status</h2>
      <div className="bot-list">
        {botVersions.map(version => {
          const bot = normalizedBots[version];
          const isSelected = selectedBot === version;
          const status = bot.status || 'unknown';
          
          // Debug each bot
          if (version === '24h') {
            console.log('Rendering 24h bot:', { version, bot, status, isSelected, normalizedBots });
          }
          
          return (
            <div
              key={version}
              className={`bot-item ${isSelected ? 'selected' : ''}`}
              onClick={() => onSelectBot(version)}
            >
              <div className="bot-header">
                <span className="bot-version">
                  {version === '5m' ? '⚡ 5-Min' :
                   version === '1h' ? '🕐 1-Hour' :
                   version === '12h' ? '🕛 12-Hour' :
                   version === '24h' ? '🌙 24-Hour' : version}
                </span>
                <span 
                  className="status-dot" 
                  style={{ backgroundColor: getStatusColor(status) }}
                />
              </div>
              <div className="bot-details">
                <div className="bot-equity">
                  {formatCurrency(bot.equity || 0)}
                </div>
                <div className="bot-signals">
                  {bot.signals_count || 0} signals
                </div>
              </div>
            </div>
          );
        })}
        <div
          className={`bot-item ${selectedBot === 'logs' ? 'selected' : ''}`}
          onClick={() => onSelectBot('logs')}
        >
          <div className="bot-header">
            <span className="bot-version">📋 Logs & Emitters</span>
            <span className="status-dot" style={{ backgroundColor: 'hsl(var(--primary))' }} />
          </div>
          <div className="bot-details">
            <div className="bot-signals" style={{ marginTop: '0.5rem' }}>
              View logs and emitter data
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BotStatus;