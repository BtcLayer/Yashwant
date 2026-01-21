# Log Validation Script

## Purpose
Validates that all log files follow the canonical schema and path pattern established in TASK-4.

## Canonical Log Pattern
```
paper_trading_outputs/{timeframe}/logs/{stream}/date=YYYY-MM-DD/asset={symbol}/{stream}.jsonl
```

## Usage

### Basic validation
```bash
python scripts/validate_logs.py
```

### Validate specific timeframe
```bash
python scripts/validate_logs.py --root paper_trading_outputs/1h
```

### Strict mode (warnings = errors)
```bash
python scripts/validate_logs.py --strict
```

## What It Checks

### 1. Path Structure
- ✅ Logs are in `logs/` directory
- ✅ Date partition exists: `date=YYYY-MM-DD`
- ✅ Asset partition exists: `asset={symbol}`
- ✅ Proper nesting: `logs/{stream}/date=.../asset=.../{stream}.jsonl`

### 2. File Format
- ✅ Valid JSONL (one JSON object per line)
- ✅ No corrupted JSON

### 3. Schema Validation
- ✅ Required fields present for each stream type
- ✅ Field types are correct

### 4. Deprecated Paths
- ⚠️ Warns about non-partitioned logs
- ⚠️ Warns about logs in `logs/default/`

## Exit Codes
- `0` - All validations passed
- `1` - Validation failures found

## Stream Schemas

### signals
Required: `ts`, `symbol`, `asset`

### execution_log
Required: `ts`, `asset`, `side`, `fill_px`, `fill_qty`

### costs_log
Required: `ts`, `asset`, `trade_notional`, `fee_bps`

### pnl_equity_log
Required: `asset`, `equity_value`

### kpi_scorecard
Required: `asset`, `event`

## CI Integration

Add to `.github/workflows/validate-logs.yml`:

```yaml
name: Validate Logs

on:
  push:
    paths:
      - 'paper_trading_outputs/**/*.jsonl'
  pull_request:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Validate 5m logs
        run: python scripts/validate_logs.py --root paper_trading_outputs/5m
      - name: Validate 1h logs
        run: python scripts/validate_logs.py --root paper_trading_outputs/1h
```

## Examples

### Valid log path
```
✅ paper_trading_outputs/5m/logs/signals/date=2026-01-20/asset=BTCUSDT/signals.jsonl
```

### Invalid log paths
```
❌ paper_trading_outputs/5m/logs/signals/signals.jsonl (no partitions)
❌ paper_trading_outputs/5m/logs/default/signals/signals.jsonl (deprecated namespace)
❌ paper_trading_outputs/5m/logs/signals/date=2026-01-20/signals.jsonl (missing asset partition)
```

## Troubleshooting

### "Missing date partition"
Your logs are not using date-based partitioning. Update your logging code to use the canonical pattern.

### "Missing asset partition"
Your logs are not using asset-based partitioning. Ensure `asset` or `symbol` is passed to the logging function.

### "Missing required fields"
A log record is missing mandatory fields. Check the stream schema above and ensure all required fields are included.

## Maintenance

When adding new log streams:
1. Add the stream to `STREAM_SCHEMAS` in `validate_logs.py`
2. Define required fields for the stream
3. Update this README with the new schema
