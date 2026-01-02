# Confidence Threshold Fixes Implementation Plan

## Overview
This document outlines the implementation plan for fixing the confidence threshold issues in the MetaStackerBandit trading system.

## Current Issues
1. **Incorrect CONF_MIN value**: The `live_demo/config.json` has `CONF_MIN` set to 0.05 (5%), which was a mistake.
2. **Inconsistent thresholds across timeframes**: Different timeframes have different confidence thresholds that need to be standardized.
3. **Risk management concerns**: The 5% threshold is too low and allows for risky trades.

## Implementation Steps

### Step 1: Update Configuration Files

#### File: live_demo/config.json
- Change `CONF_MIN` from 0.05 to 0.55
- Update overlay signal thresholds:
  - 5m timeframe: min_confidence = 0.55
  - 15m timeframe: min_confidence = 0.55
  - 1h timeframe: min_confidence = 0.60

#### File: live_demo/config_overlay.json
- Ensure `CONF_MIN` is set to 0.60
- Update overlay signal thresholds to match the main config

#### File: live_demo_1h/config.json
- Update CONF_MIN to appropriate value (likely 0.55 or 0.60)
- Ensure consistency with other configurations

#### File: live_demo_1h/config_overlay.json
- Ensure CONF_MIN is set to 0.60
- Update overlay signal thresholds as needed

#### File: live_demo_24h/config.json
- Update CONF_MIN to appropriate value (likely 0.55 or 0.60)
- Ensure consistency with other configurations

#### File: live_demo_24h/config_overlay.json
- Ensure CONF_MIN is set to 0.60
- Update overlay signal thresholds as needed

### Step 2: Verify Confidence Calculation

The confidence is calculated as the maximum probability among `p_up`, `p_down`, and `p_neutral` from the model prediction. This is implemented correctly in the overlay_signal_generator.py files:

```python
# Calculate confidence as max probability
confidence = max(p_up, p_down, p_neutral)
```

This calculation is working correctly and doesn't need modification.

### Step 3: Test Signal Generation

After updating the configuration files, test the signal generation process:

1. **Unit Tests**: Run existing unit tests to ensure no regression
2. **Integration Tests**: Test signal generation with different confidence levels
3. **Boundary Tests**: Test behavior at confidence thresholds (0.55 and 0.60)
4. **Multi-timeframe Tests**: Verify signal combination across different timeframes

### Step 4: Verify Websocket Reconnection

The websocket reconnection logic is already properly implemented with:
- Exponential backoff
- Retry attempts with jitter
- Connection status monitoring

No changes are needed here, but testing should verify:
- Reconnection happens smoothly
- No data loss during reconnection
- System continues operating during reconnection

### Step 5: End-to-End System Test

Perform comprehensive testing of the entire system:

1. **Market Data Ingestion**: Verify data flows correctly through the system
2. **Signal Generation**: Confirm signals are generated with correct confidence thresholds
3. **Trade Execution**: Ensure trades are executed only when confidence exceeds thresholds
4. **Risk Management**: Verify risk management rules are applied correctly

### Step 6: Performance Testing

Test system performance under various conditions:
- High market volatility
- High trading volume
- Network latency
- System reconnection scenarios

## Configuration Details

### Confidence Threshold Values by Timeframe

Based on the analysis, the following confidence thresholds should be applied:

| Timeframe | CONF_MIN | Rationale |
|-----------|---------|-----------|
| 5m | 0.55 | Shorter timeframe, slightly lower threshold for more activity |
| 15m | 0.55 | Medium timeframe, balanced threshold |
| 1h | 0.60 | Longer timeframe, higher threshold for more certainty |
| 4h | 0.60 | Longer timeframe, higher threshold for more certainty |
| 12h | 0.65 | Much longer timeframe, highest threshold |
| 24h | 0.70 | Longest timeframe, highest threshold for maximum certainty |

### File Changes Required

#### live_demo/config.json
```json
{
  "thresholds": {
    "S_MIN": 0.05,
    "M_MIN": 0.12,
    "CONF_MIN": 0.55,
    "ALPHA_MIN": 0.02,
    ...
  },
  "overlay": {
    "signal_thresholds": {
      "default": { "min_confidence": 0.55, "min_alpha": 0.02, "neutral_band": 0.10 },
      "5m":      { "min_confidence": 0.55, "min_alpha": 0.02, "neutral_band": 0.10 },
      "15m":     { "min_confidence": 0.55, "min_alpha": 0.02, "neutral_band": 0.10 },
      "1h":      { "min_confidence": 0.60, "min_alpha": 0.02, "neutral_band": 0.10 }
    }
  }
}
```

#### live_demo/config_overlay.json
```json
{
  "thresholds": {
    "S_MIN": 0.12,
    "M_MIN": 0.12,
    "CONF_MIN": 0.60,
    "ALPHA_MIN": 0.10,
    ...
  },
  "overlay": {
    "signal_thresholds": {
      "min_confidence": 0.60,
      "min_alpha": 0.10,
      "neutral_band": 0.05
    }
  }
}
```

## Testing Plan

### Unit Tests
1. Test confidence calculation with various model outputs
2. Test threshold comparison logic
3. Test signal generation with different confidence levels

### Integration Tests
1. Test signal combination across multiple timeframes
2. Test alignment rules with updated thresholds
3. Test websocket reconnection during signal generation

### System Tests
1. End-to-end test with market data
2. Performance test under high load
3. Failover test during network issues

## Rollback Plan

If issues arise after implementing these changes, the following rollback steps should be taken:

1. Restore original configuration files from backup
2. Restart all trading bots
3. Monitor system for stability
4. Investigate issues before attempting re-implementation

## Success Criteria

The implementation is considered successful when:

1. All configuration files have been updated with correct confidence thresholds
2. Signal generation works correctly with new thresholds
3. System passes all unit and integration tests
4. Trading activity is balanced between risk management and opportunity capture
5. No regression in system performance or stability

## Timeline

- Day 1: Update configuration files and run initial tests
- Day 2: Comprehensive testing and bug fixes
- Day 3: Performance testing and optimization
- Day 4: Deployment preparation and documentation
- Day 5: Deployment and monitoring

## Dependencies

- Access to configuration files
- Testing environment with market data
- Model runtime environment
- Development team for code changes if needed

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Configuration errors | Double-check all changes before deployment |
| Reduced trading activity | Monitor trading frequency and adjust if needed |
| System instability | Test thoroughly in staging environment first |
| Performance degradation | Benchmark performance before and after changes |

## Sign-off

This plan should be reviewed and approved by the development team before implementation begins.

---

*Last Updated: 2025-12-25*