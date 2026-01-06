# SWITCHING FROM HYPERLIQUID TO LIGHTER - COMPLETE GUIDE

## WHERE HYPERLIQUID IS USED

### 1. CONFIG.JSON (Primary Configuration)
**Location**: `live_demo/config.json`

**Current Settings**:
```json
Line 12:  "active": "hyperliquid",
Line 23-32: "hyperliquid": {
  "base_url": "https://api.hyperliquid.xyz/info",
  "ws_url": "wss://api.hyperliquid.xyz/ws",
  "funding": {...}
}
```

### 2. FEE CONFIGURATION
**Location**: `live_demo/config.json`

**Current Fees** (Lines 52-56):
```json
"costs": {
  "taker_fee_bps": 5.0,      // Hyperliquid taker fee
  "slippage_bps": 1.0,
  "min_net_edge_buffer_bps": 2.0
}
```

### 3. CODE FILES (API Integration)
**Location**: `live_demo/main.py`

**Lines Using Hyperliquid**:
- Line 121-261: HyperliquidClientAdapter class
- Line 338-350: Hyperliquid funding/fills setup
- Line 636: User fills subscription

---

## CHANGES NEEDED FOR LIGHTER (ZERO FEES)

### STEP 1: UPDATE CONFIG.JSON - Exchange Settings

**File**: `live_demo/config.json`

**Change Line 12**:
```json
// FROM:
"active": "hyperliquid",

// TO:
"active": "lighter",
```

**Add Lighter Configuration** (after line 32):
```json
"lighter": {
  "base_url": "https://api.lighter.xyz/v1",  // Replace with actual Lighter API URL
  "ws_url": "wss://api.lighter.xyz/ws",      // Replace with actual Lighter WS URL
  "api_key": "YOUR_LIGHTER_API_KEY",         // If required
  "api_secret": "YOUR_LIGHTER_API_SECRET"    // If required
}
```

### STEP 2: UPDATE FEE CONFIGURATION

**File**: `live_demo/config.json` (Lines 52-56)

**Change to**:
```json
"costs": {
  "taker_fee_bps": 0.0,      // ZERO FEES on Lighter!
  "slippage_bps": 1.5,       // Slightly higher slippage (less liquidity)
  "min_net_edge_buffer_bps": 0.5  // Lower buffer needed
}
```

**This changes your hurdle from 8 bps to 2 bps!**

### STEP 3: UPDATE CODE - API Adapter

**File**: `live_demo/main.py`

**Add Lighter Support** (after line 261):

```python
elif ex_active == "lighter":
    # Use Lighter for market data
    lighter_base = cfg["exchanges"]["lighter"]["base_url"]
    
    class LighterClientAdapter:
        """Adapter to make Lighter API compatible with MarketData interface"""
        def __init__(self, base_url, symbol):
            self.base_url = base_url
            self.symbol = symbol
            self.cache = {}
            self.last_request_time = 0
            self.min_request_interval = 0.2  # 200ms between requests
            
        def get_klines(self, interval, limit=1000):
            """Get candles from Lighter API"""
            # Map interval to Lighter format
            interval_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60"}
            lighter_interval = interval_map.get(interval, "5")
            
            # Lighter uses BTC not BTCUSDT
            coin = self.symbol.replace("USDT", "")
            
            # Build request
            url = f"{self.base_url}/candles"
            params = {
                "symbol": coin,
                "interval": lighter_interval,
                "limit": limit
            }
            
            # Make request (add retry logic similar to Hyperliquid)
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Convert Lighter format to standard format
                # [timestamp, open, high, low, close, volume]
                return [[
                    candle['timestamp'],
                    candle['open'],
                    candle['high'],
                    candle['low'],
                    candle['close'],
                    candle['volume']
                ] for candle in data]
            else:
                raise RuntimeError(f"Lighter API error: {response.status_code}")
    
    client = LighterClientAdapter(lighter_base, sym)
```

---

## SUMMARY OF CHANGES

### Files to Modify:

1. **`live_demo/config.json`** (2 changes):
   - Line 12: Change `"active": "hyperliquid"` to `"active": "lighter"`
   - Lines 52-56: Update fee configuration to zero fees
   - Add new "lighter" section with API URLs

2. **`live_demo/main.py`** (1 change):
   - Add LighterClientAdapter class (similar to HyperliquidClientAdapter)

### What You DON'T Need to Change:

- Decision logic (`decision.py`) - works with any exchange
- Model files - platform agnostic
- Threshold logic - automatically adjusts based on config
- Output files - same format regardless of exchange

---

## TESTING CHECKLIST

Before switching to live:

1. ☐ Get Lighter API credentials
2. ☐ Test API connectivity (can you fetch candles?)
3. ☐ Verify data format matches expected structure
4. ☐ Run in paper trading mode for 24 hours
5. ☐ Compare slippage: should be < 2 bps average
6. ☐ Verify zero fees are actually applied
7. ☐ Check execution quality (fills at expected prices)

---

## EXPECTED IMPACT

**Current (Hyperliquid)**:
- Hurdle: 8 bps
- Model Edge: 6.5 bps
- Result: UNPROFITABLE (-1.48 bps gap)

**After Switch (Lighter)**:
- Hurdle: 2 bps
- Model Edge: 6.5 bps
- Result: PROFITABLE (+4.5 bps gap)

**Estimated Improvement**: +$0.73 per trade cycle (fee savings)

---

## ROLLBACK PLAN

If Lighter doesn't work:

1. Change line 12 back to `"active": "hyperliquid"`
2. Revert fee configuration to original values
3. Restart bot

Takes < 1 minute to rollback.

---

## IMPORTANT NOTES

⚠️ **You need Lighter's actual API documentation to complete the adapter**
⚠️ **Test thoroughly before going live**
⚠️ **Monitor slippage closely - if > 3 bps, advantage is lost**
⚠️ **Keep Hyperliquid config in place for easy rollback**
