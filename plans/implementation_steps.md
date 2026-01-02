# Detailed Implementation Steps

## Overview
This document provides a step-by-step implementation guide for fixing the timeframe trading issues in MetaStackerBandit. Each step is broken down into manageable parts with specific file locations and changes needed.

## Phase 1: Critical Fixes (Week 1, Days 1-2)

### Step 1.1: Fix 1h ALPHA_MIN Threshold
**Priority**: HIGH
**Files**: `live_demo_1h/config.json`
**Issue**: ALPHA_MIN is set to 0.05 but should be 0.10 to align with CONF_MIN of 0.60

**Implementation Steps**:
1. Open `live_demo_1h/config.json`
2. Locate line 44: `"ALPHA_MIN": 0.05,`
3. Change to: `"ALPHA_MIN": 0.10,`
4. Save the file
5. Test the configuration by running the 1h bot in dry-run mode

**Verification**:
- Check that ALPHA_MIN is now 0.10 in the config file
- Verify that the 1h bot starts without configuration errors
- Monitor for improved trading activity in 1h timeframe

### Step 1.2: Fix 5m Precision Error
**Priority**: HIGH
**Files**: `run_5m_debug.py`, `live_demo/risk_and_exec.py`
**Issue**: "APIError(code=-1111): Precision is over the maximum defined for this asset"

**Implementation Steps**:
1. Open `run_5m_debug.py`
2. Locate line 15: `print(f"\n❌ ERROR: {type(e).__name__}: {e}")`
3. Remove the Unicode character (❌) or implement proper encoding:
   ```python
   print(f"\nERROR: {type(e).__name__}: {e}")
   ```
4. Open `live_demo/risk_and_exec.py`
5. Locate the order execution function (around line 550)
6. Add precision calculation for order quantities:
   ```python
   def calculate_precision(self, quantity):
       # Calculate appropriate precision for the exchange
       return round(quantity, 3)  # Adjust precision as needed
   ```
7. Apply precision calculation before creating orders:
   ```python
   qty = self.calculate_precision(qty)
   ```
8. Save the files
9. Test the 5m bot with a small trade

**Verification**:
- Run 5m bot and verify no precision errors occur
- Check that orders are executed successfully
- Monitor logs for successful trades

### Step 1.3: Fix Error Logging
**Priority**: MEDIUM
**Files**: `run_5m_debug.py`, `run_1h.py`, `run_12h.py`, `run_24h.py`
**Issue**: Unicode encoding errors in error logging

**Implementation Steps**:
1. For each run file (5m, 1h, 12h, 24h):
   - Open the file
   - Locate any print statements with Unicode characters
   - Remove or replace Unicode characters with plain text
   - Example: Replace `❌` with `ERROR`
2. Save all files
3. Test error handling by intentionally causing an error

**Verification**:
- Verify no Unicode encoding errors occur
- Check that errors are logged properly
- Ensure error messages are readable

## Phase 2: Model Performance Enhancement (Week 1, Days 3-5)

### Step 2.1: Investigate Model Performance
**Priority**: HIGH
**Files**: Model files in each timeframe's models directory
**Issue**: Longer timeframes showing very low confidence values

**Implementation Steps**:
1. Check model files in each timeframe:
   - `live_demo/models/LATEST.json`
   - `live_demo_1h/models/LATEST.json`
   - `live_demo_12h/models/LATEST.json`
   - `live_demo_24h/models/LATEST.json`
2. Compare model creation dates and versions
3. Check if models are properly loaded by each timeframe
4. Analyze feature files to ensure consistency:
   - `live_demo_1h/features.py`
   - `live_demo_12h/features.py`
   - `live_demo_24h/features.py`
5. Run model diagnostics to identify performance issues

**Verification**:
- Document model versions and creation dates
- Identify any missing or corrupted model files
- Determine if models are generating appropriate confidence values

### Step 2.2: Model Retraining (if needed)
**Priority**: MEDIUM
**Files**: Model training scripts
**Issue**: Models may need retraining to improve confidence values

**Implementation Steps**:
1. If models are identified as problematic:
   - Locate model training scripts
   - Prepare training data for each timeframe
   - Retrain models with updated parameters
   - Save new models to appropriate directories
2. Update LATEST.json files to point to new models
3. Test retrained models in dry-run mode

**Verification**:
- Verify new models generate higher confidence values
- Check that trading activity increases in longer timeframes
- Ensure model stability over multiple runs

### Step 2.3: Feature Engineering
**Priority**: MEDIUM
**Files**: Feature files in each timeframe
**Issue**: Features may need enhancement for longer timeframes

**Implementation Steps**:
1. Analyze current features in each timeframe:
   - `live_demo_1h/features.py`
   - `live_demo_12h/features.py`
   - `live_demo_24h/features.py`
2. Identify features that could be improved:
   - Add timeframe-specific features
   - Enhance existing features
   - Remove unhelpful features
3. Implement feature improvements
4. Test feature changes with models

**Verification**:
- Verify feature improvements increase confidence values
- Check that features are stable and not overfitting
- Ensure features work well across all timeframes

## Phase 3: System Optimization (Week 2, Day 4)

### Step 3.1: Overlay Signal Alignment
**Priority**: MEDIUM
**Files**: Config files for each timeframe
**Issue**: Overlay signal thresholds may be misaligned

**Implementation Steps**:
1. Check overlay signal thresholds in each config:
   - `live_demo/config.json` (lines 127-132)
   - `live_demo_1h/config.json` (lines 127-132)
   - `live_demo_12h/config.json` (lines 127-133)
   - `live_demo_24h/config.json` (lines 127-130)
2. Verify alignment with main CONF_MIN and ALPHA_MIN values
3. Fix any misalignments:
   - Ensure overlay thresholds match or are stricter than main thresholds
   - Verify consistency across timeframes
4. Save updated config files
5. Test overlay signal generation

**Verification**:
- Verify overlay signals are properly aligned
- Check that overlay signals don't conflict with main signals
- Ensure consistent behavior across timeframes

### Step 3.2: Websocket Connection Stability
**Priority**: MEDIUM
**Files**: `hyperliquid_listener.py` in each timeframe
**Issue**: Websocket connections may be unstable

**Implementation Steps**:
1. Check websocket implementation in each timeframe:
   - `live_demo/hyperliquid_listener.py`
   - `live_demo_1h/hyperliquid_listener.py`
   - `live_demo_12h/hyperliquid_listener.py`
   - `live_demo_24h/hyperliquid_listener.py`
2. Verify reconnection logic is implemented
3. Check error handling for websocket disconnections
4. Enhance connection stability if needed:
   - Add exponential backoff
   - Improve error handling
   - Add connection health monitoring
5. Test websocket connections

**Verification**:
- Verify stable connections across all timeframes
- Check proper reconnection after disconnections
- Ensure data flow is consistent

### Step 3.3: Execution Optimization
**Priority**: MEDIUM
**Files**: Execution-related files in each timeframe
**Issue**: Execution logic may need optimization

**Implementation Steps**:
1. Review execution logic in each timeframe:
   - `live_demo/risk_and_exec.py`
   - `live_demo_1h/risk_and_exec.py`
   - `live_demo_12h/risk_and_exec.py`
   - `live_demo_24h/risk_and_exec.py`
2. Identify optimization opportunities:
   - Reduce latency
   - Improve error handling
   - Enhance order management
3. Implement optimizations
4. Test execution improvements

**Verification**:
- Verify improved execution speed and reliability
- Check that errors are handled gracefully
- Ensure order management is robust

## Phase 4: System Readiness (Week 2, Day 5 - Week 3)

### Step 4.1: Comprehensive Testing
**Priority**: HIGH
**Files**: All system files
**Issue**: Need to verify all fixes work together

**Implementation Steps**:
1. Create comprehensive test plan:
   - Test each timeframe individually
   - Test all timeframes together
   - Test error scenarios
   - Test edge cases
2. Execute test plan
3. Document test results
4. Fix any issues found

**Verification**:
- Verify all timeframes are trading actively
- Check that all fixes work as expected
- Ensure system stability under various conditions

### Step 4.2: Performance Monitoring
**Priority**: MEDIUM
**Files**: Monitoring-related files
**Issue**: Need ongoing performance monitoring

**Implementation Steps**:
1. Review current monitoring capabilities:
   - Check existing monitoring files
   - Identify gaps in monitoring
2. Enhance monitoring if needed:
   - Add more metrics
   - Improve alerting
   - Enhance reporting
3. Test monitoring system

**Verification**:
- Verify comprehensive monitoring is in place
- Check that alerts are working correctly
- Ensure reporting provides useful insights

### Step 4.3: Deployment Readiness
**Priority**: HIGH
**Files**: Deployment-related files
**Issue**: System needs to be ready for live deployment

**Implementation Steps**:
1. Create deployment checklist:
   - Verify all fixes are complete
   - Check system stability
   - Ensure proper documentation
   - Verify risk management is in place
2. Execute deployment checklist
3. Prepare deployment plan
4. Get final approval for deployment

**Verification**:
- Verify system is ready for live deployment
- Check that all requirements are met
- Ensure smooth deployment process

## Testing Protocol

### Unit Testing
1. Test each fix individually
2. Verify expected behavior
3. Check for unintended side effects

### Integration Testing
1. Test multiple fixes together
2. Verify system-wide compatibility
3. Check for conflicts between fixes

### System Testing
1. Test entire system with all fixes
2. Verify end-to-end functionality
3. Check system stability under load

### Performance Testing
1. Test system performance
2. Verify response times
3. Check resource usage

## Rollback Plan

### If Issues Arise
1. Identify the problematic fix
2. Revert to previous version
3. Analyze the issue
4. Implement corrected fix

### Rollback Triggers
1. System instability
2. Trading failures
3. Performance degradation
4. Unexpected behavior

## Success Metrics

### 5m Timeframe
- No precision errors
- Active and profitable trading
- Proper error logging

### 1h Timeframe
- ALPHA_MIN correctly set to 0.10
- Active trading resumed
- Improved confidence values

### 12h Timeframe
- Active trading resumed
- Improved confidence values

### 24h Timeframe
- Active trading resumed
- Improved confidence values

### System Overall
- All timeframes trading actively
- Stable websocket connections
- Proper error logging
- Ready for live deployment

## Conclusion

This detailed implementation plan provides step-by-step instructions for fixing all identified issues. By following these steps systematically, we can restore active trading across all timeframes and ensure the system is ready for live deployment.