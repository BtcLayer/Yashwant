# Comprehensive Test Plan for MetaStackerBandit System

## Overview
This document outlines a comprehensive test plan to verify all components of the MetaStackerBandit system work together correctly after implementing the confidence threshold fixes.

## Test Objectives
1. Verify that confidence thresholds are correctly implemented across all timeframes
2. Ensure signal generation works properly with updated thresholds
3. Confirm websocket reconnection logic functions correctly
4. Validate end-to-end system functionality
5. Identify any remaining issues preventing full operational status

## Test Scope

### Component Tests
1. **Configuration Files**
   - Verify all configuration files have correct confidence thresholds
   - Ensure consistency across all configuration files
   - Test configuration loading and parsing

2. **Model Runtime**
   - Test model inference with various inputs
   - Verify confidence calculation (max of p_up, p_down, p_neutral)
   - Test model performance under different market conditions

3. **Signal Generation**
   - Test signal generation for each timeframe (5m, 15m, 1h, 4h, 12h, 24h)
   - Verify confidence thresholds are applied correctly
   - Test signal combination across multiple timeframes

4. **Websocket Connectivity**
   - Test initial connection to Hyperliquid
   - Verify websocket reconnection logic
   - Test data flow during reconnection

### Integration Tests
1. **Overlay System**
   - Test overlay feature calculation
   - Verify signal alignment rules
   - Test unified overlay system functionality

2. **Signal Combiner**
   - Test signal combination with different alignment rules
   - Verify conflict resolution between timeframes
   - Test weighted average combination

3. **Risk Management**
   - Verify risk management rules are applied
   - Test position sizing based on confidence
   - Verify stop-loss and take-profit functionality

### System Tests
1. **End-to-End Trading**
   - Test complete trading workflow from market data to execution
   - Verify trading activity with updated confidence thresholds
   - Test system behavior during high volatility

2. **Performance Testing**
   - Test system performance under high load
   - Verify response times during peak activity
   - Test system stability over extended periods

3. **Failover Testing**
   - Test system behavior during network outages
   - Verify data recovery after reconnection
   - Test system resilience to component failures

## Test Environment

### Hardware Requirements
- Server with sufficient CPU and memory for all components
- Network connection to Hyperliquid API
- Storage for logs and market data

### Software Requirements
- Python 3.8+ with required packages
- MetaStackerBandit codebase
- Test data sets
- Monitoring tools

### Test Data
- Historical market data for backtesting
- Recent market data for validation
- Edge case scenarios for stress testing

## Test Cases

### Configuration Tests

#### Test Case 1.1: Verify Configuration Files
**Description**: Verify all configuration files have correct confidence thresholds
**Steps**:
1. Check CONF_MIN value in each config.json file
2. Verify overlay signal thresholds in each config_overlay.json file
3. Ensure consistency across all configuration files
**Expected Result**: All configuration files have correct confidence thresholds (0.55 for shorter timeframes, 0.60 for longer timeframes)

#### Test Case 1.2: Test Configuration Loading
**Description**: Test that configuration files are loaded and parsed correctly
**Steps**:
1. Load each configuration file
2. Verify all required parameters are present
3. Check that values are of correct type
**Expected Result**: All configuration files load without errors and all parameters are correctly parsed

### Model Runtime Tests

#### Test Case 2.1: Test Model Inference
**Description**: Test model inference with various inputs
**Steps**:
1. Prepare test feature vectors
2. Run model inference
3. Verify output contains p_up, p_down, p_neutral, and s_model
**Expected Result**: Model returns valid predictions with all required fields

#### Test Case 2.2: Verify Confidence Calculation
**Description**: Verify confidence is calculated as max of p_up, p_down, p_neutral
**Steps**:
1. Create test predictions with known probabilities
2. Calculate confidence using max function
3. Verify result matches expected value
**Expected Result**: Confidence equals max(p_up, p_down, p_neutral)

### Signal Generation Tests

#### Test Case 3.1: Test Signal Generation for Each Timeframe
**Description**: Test signal generation for each timeframe with correct thresholds
**Steps**:
1. Generate signals for each timeframe (5m, 15m, 1h, 4h, 12h, 24h)
2. Verify signals respect timeframe-specific confidence thresholds
3. Check that signals below threshold are set to neutral
**Expected Result**: Signals are generated correctly with appropriate thresholds applied

#### Test Case 3.2: Test Signal Combination
**Description**: Test signal combination across multiple timeframes
**Steps**:
1. Generate signals for multiple timeframes
2. Apply combination rules
3. Verify final combined signal
**Expected Result**: Combined signal respects alignment rules and timeframe weights

### Websocket Tests

#### Test Case 4.1: Test Initial Connection
**Description**: Test initial websocket connection to Hyperliquid
**Steps**:
1. Initialize websocket connection
2. Verify successful connection
3. Check subscription to trade data
**Expected Result**: Websocket connects successfully and receives trade data

#### Test Case 4.2: Test Websocket Reconnection
**Description**: Test websocket reconnection logic
**Steps**:
1. Establish websocket connection
2. Simulate connection failure
3. Verify reconnection with exponential backoff
4. Check data flow after reconnection
**Expected Result**: Websocket reconnects successfully with no data loss

### Integration Tests

#### Test Case 5.1: Test Overlay System
**Description**: Test overlay feature calculation and signal generation
**Steps**:
1. Initialize overlay system
2. Add market data
3. Generate overlay signals
4. Verify signal accuracy
**Expected Result**: Overlay system generates accurate signals for all timeframes

#### Test Case 5.2: Test Signal Combiner
**Description**: Test signal combination with different alignment rules
**Steps**:
1. Create test signals for multiple timeframes
2. Apply each alignment rule (agreement, neutral_override, weighted_average)
3. Verify combined signal for each rule
**Expected Result**: Signal combiner applies alignment rules correctly

### System Tests

#### Test Case 6.1: End-to-End Trading Test
**Description**: Test complete trading workflow
**Steps**:
1. Ingest market data
2. Generate signals
3. Execute trades (in test mode)
4. Verify trade execution
**Expected Result**: Complete trading workflow functions correctly

#### Test Case 6.2: Performance Test
**Description**: Test system performance under high load
**Steps**:
1. Simulate high market activity
2. Monitor system response times
3. Check resource utilization
4. Verify no dropped connections or data
**Expected Result**: System maintains performance under high load

## Test Execution

### Test Sequence
1. **Phase 1: Component Tests** - Verify individual components work correctly
2. **Phase 2: Integration Tests** - Verify components work together
3. **Phase 3: System Tests** - Verify end-to-end functionality
4. **Phase 4: Performance Tests** - Verify system performance
5. **Phase 5: Regression Tests** - Verify no regression in existing functionality

### Test Schedule
- **Day 1**: Component tests (Configuration, Model Runtime, Signal Generation)
- **Day 2**: Integration tests (Overlay System, Signal Combiner, Risk Management)
- **Day 3**: System tests (End-to-End, Performance, Failover)
- **Day 4**: Bug fixes and retesting
- **Day 5**: Final verification and documentation

## Success Criteria

### Test Coverage
- 100% of critical test cases pass
- 95% of all test cases pass
- All high-priority bugs resolved

### Performance Criteria
- System response time < 1 second under normal load
- System response time < 3 seconds under high load
- 99.9% uptime during testing period
- No data loss during reconnection

### Functional Criteria
- All confidence thresholds applied correctly
- Signal generation works for all timeframes
- Websocket reconnection functions properly
- End-to-end trading workflow completes successfully

## Test Deliverables

1. **Test Report**: Detailed report of all test results
2. **Bug List**: List of all identified bugs with severity and priority
3. **Performance Metrics**: System performance measurements
4. **Test Logs**: Detailed logs of all test executions
5. **Test Data**: All test data used for verification

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Incomplete test coverage | Review test cases against requirements |
| Test environment issues | Prepare backup test environment |
| Test data inaccuracies | Validate test data before use |
| Performance bottlenecks | Identify and optimize critical paths |

## Sign-off

This test plan should be reviewed and approved by the development team before execution begins.

---

*Last Updated: 2025-12-25*