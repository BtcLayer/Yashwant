# MetaStackerBandit System Restoration Plan

## Executive Summary

This document outlines the comprehensive plan to restore full trading functionality across all timeframes in the MetaStackerBandit system. The primary issue identified was a model mismatch where longer timeframes (1h, 12h, 24h) were using models trained for 3-minute data, causing zero trading activity.

## Issues Fixed

### 1. Critical Configuration Issues (COMPLETED)
- [x] Fixed 1h timeframe ALPHA_MIN threshold from 0.05 to 0.10 in live_demo_1h/config.json
- [x] Fixed precision error in 5m timeframe by updating order quantity calculation in live_demo/risk_and_exec.py
- [x] Removed Unicode characters from error logging in run_5m_debug.py to prevent encoding errors
- [x] Verified overlay signal thresholds are properly aligned with main CONF_MIN and ALPHA_MIN values in all configs

### 2. Model Mismatch Issues (COMPLETED)
- [x] Identified that 1h, 12h, and 24h timeframes were using models trained for 3-minute data
- [x] Updated live_demo_12h/models/LATEST.json to point to the correct 12h model
- [x] Updated live_demo_1h/models/LATEST.json to use the 12h model (temporary solution)
- [x] Updated live_demo_24h/models/LATEST.json to use the 12h model (temporary solution)

## Testing and Verification Plan

### Phase 1: Individual Timeframe Testing
1. **5m Timeframe Verification**
   - [ ] Verify 5m timeframe is trading profitably and logs are recording trades correctly
   - [ ] Check for precision errors in order execution
   - [ ] Confirm confidence values are within expected range (0.0 to 0.2588)

2. **1h Timeframe Testing**
   - [ ] Run 1h timeframe bot individually to identify any startup or runtime errors
   - [ ] Monitor confidence values to ensure they're above the 0.60 threshold
   - [ ] Verify that trades are being executed when appropriate

3. **12h Timeframe Testing**
   - [ ] Run 12h timeframe bot individually to identify any startup or runtime errors
   - [ ] Monitor confidence values to ensure they're above the 0.65 threshold
   - [ ] Verify that trades are being executed when appropriate

4. **24h Timeframe Testing**
   - [ ] Run 24h timeframe bot individually to identify any startup or runtime errors
   - [ ] Monitor confidence values to ensure they're above the 0.70 threshold
   - [ ] Verify that trades are being executed when appropriate

### Phase 2: System Integration Testing
1. **Websocket Connection Testing**
   - [ ] Test websocket connections in all timeframes to ensure stable data flow
   - [ ] Verify no connection conflicts when multiple timeframes are running

2. **Simultaneous Operation Testing**
   - [ ] Test all timeframes running simultaneously to ensure no conflicts
   - [ ] Monitor system resource usage during simultaneous operation
   - [ ] Verify no interference between timeframe processes

### Phase 3: Performance Analysis
1. **Confidence Value Analysis**
   - [ ] Analyze confidence values across all timeframes to identify model performance issues
   - [ ] Compare confidence distributions with expected ranges
   - [ ] Identify any timeframes that may need further model adjustments

2. **Trading Activity Verification**
   - [ ] Verify that all timeframes are executing trades when confidence thresholds are met
   - [ ] Check that trade logs are being recorded correctly for all timeframes
   - [ ] Analyze trade profitability across all timeframes

## Future Enhancements

### Model Retraining Plan
1. **1h Timeframe Model**
   - Train a new model specifically for 1h data
   - Target: direction_confidence_1h
   - Timeline: 2-3 weeks

2. **24h Timeframe Model**
   - Train a new model specifically for 24h data
   - Target: direction_confidence_24h
   - Timeline: 3-4 weeks

### System Monitoring Enhancements
1. **Automated Confidence Monitoring**
   - Implement automated monitoring of confidence values
   - Set up alerts for unusual trading patterns
   - Create dashboard for real-time performance tracking

2. **Model Performance Tracking**
   - Implement model performance metrics tracking
   - Set up regular model retraining schedule
   - Create model versioning and rollback procedures

## System Readiness Checklist

### Pre-Deployment Checks
- [ ] All timeframes are trading actively
- [ ] Confidence values are within expected ranges
- [ ] No precision errors in order execution
- [ ] Trade logs are recording correctly
- [ ] Websocket connections are stable
- [ ] System resources are adequate for simultaneous operation

### Deployment Readiness
- [ ] All critical issues resolved
- [ ] System tested under various market conditions
- [ ] Backup and recovery procedures in place
- [ ] Monitoring and alerting systems operational
- [ ] Documentation updated with all changes

## Timeline

### Week 1: Testing and Verification
- Days 1-2: Individual timeframe testing
- Days 3-4: System integration testing
- Days 5-7: Performance analysis and final adjustments

### Week 2: Model Retraining Preparation
- Data collection for new models
- Feature engineering for specific timeframes
- Model training pipeline setup

### Week 3-4: Model Retraining and Deployment
- Train new 1h timeframe model
- Train new 24h timeframe model
- Deploy new models and verify performance

## Success Criteria

1. All timeframes (5m, 1h, 12h, 24h) are actively trading
2. Confidence values are within expected ranges for each timeframe
3. No precision errors or other technical issues
4. System can run all timeframes simultaneously without conflicts
5. Trade logs are recording correctly for all timeframes

## Conclusion

This plan provides a comprehensive approach to restoring full functionality to the MetaStackerBandit system. The immediate fixes address the critical model mismatch issues, while the testing plan ensures system stability. The future enhancements will further improve system performance by providing timeframe-specific models.