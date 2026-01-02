# Issues and Recommendations

## 1. Confidence Threshold (`CONF_MIN`) and `S_mood`

- **Issue:**
  - The system rarely reaches the original confidence threshold (55%), resulting in almost no trades.
  - Lowering `CONF_MIN` (e.g., to 2–5%) increases trade frequency but also risk, as trades are made with less certainty.
  - In November, trades occurred with low confidence and low `S_mood`, but the system was active.
  - The highest `S_mood` (25.88%) had 0 public trades due to a technical issue (websocket reconnection, now fixed).

- **Recommendations:**
  - Lowering `CONF_MIN` will increase trading activity but also risk. Consider the risk appetite before changing this value.
  - If `S_mood` is low, trades are riskier, but the system will still operate as designed.
  - With the websocket issue fixed, high `S_mood` and high confidence signals should now result in trades as expected.
  - Decide whether to:
    - Lower `CONF_MIN` to allow more trades (with higher risk), or
    - Work on improving the system's ability to reach higher confidence levels (e.g., 55%).

## 2. Test Failures and CI/CD Issues

### A. Async Test Framework Missing
- **Error:**
  - `FAILED live_demo/tests/test_integration.py::test_overlay_integration - Failed: async def functions are not natively supported.`
- **Solution:**
  - Install a suitable plugin for your async framework, e.g.:
    - `pytest-asyncio`
    - `anyio`
    - `pytest-tornasync`, `pytest-trio`, or `pytest-twisted`

### B. Attribute/Type Errors in Overlay System
- **Errors:**
  - `TypeError: ... got an unexpected keyword argument 'min_bars'`
  - `AttributeError: 'OverlaySignalGenerator' object has no attribute '_calculate_signal_components'`
  - `AttributeError: None does not have the attribute 'generate_signals'`
  - `AssertionError: 2 != 1 (test_rollup_generation)`
  - `AssertionError: unexpectedly None (test_initialization)`
- **Root Causes:**
  - Test code or system under test is calling functions with wrong/outdated arguments.
  - Classes/mocks are missing required attributes/methods.
  - Possible API drift or missing mocks.
  - Rollup generation logic is producing unexpected results.
  - Objects are unexpectedly `None`, indicating failed initialization or incorrect test setup.

### C. File Not Found
- **Error:**
  - `Error loading model: [Errno 2] No such file or directory: 'test_models/LATEST.json'`
- **Solution:**
  - Ensure the required model file exists at `test_models/LATEST.json` or update the test to use a valid path.

### D. PytestReturnNotNoneWarning
- **Warning:**
  - `Test functions should return None, but test_file_structure returned <class 'bool'>.`
- **Solution:**
  - Test functions should use `assert` statements and not return values. Refactor test functions to return `None`.

---

**Summary:**
- Address the async test support by installing the correct plugin.
- Review and update test code and mocks to match the current implementation.
- Ensure all required files exist for tests.
- Refactor test functions to comply with pytest expectations.
- For trading logic, decide on risk appetite and adjust `CONF_MIN` or improve confidence calculation as needed.
