# 5M BOT RESTART GUIDE - WITH MONITORING

## 🔄 HOW TO RESTART THE BOT

### **Step 1: Stop Current Bot**

**In the terminal running the bot:**
1. Press **Ctrl+C** to stop the current bot
2. Wait for it to shut down cleanly
3. You should see the process exit

### **Step 2: Start Fresh Bot**

**Run this command:**
```powershell
python run_5m_debug.py
```

**Expected output:**
- "Starting bot..."
- "Config loaded..."
- "Model loaded..."
- "Entering main loop..."

### **Step 3: Start Monitor (In New Terminal)**

**Open a NEW terminal and run:**
```powershell
python monitor_5m_realtime.py
```

**This will show you:**
- ✅ Real-time trade status
- ✅ Confidence levels
- ✅ Latest predictions
- ✅ System alerts
- ✅ Updates every 10 seconds

---

## 📊 WHAT TO WATCH FOR

### **First 5 Minutes:**
- ✅ Bot starts without errors
- ✅ "Config loaded" message
- ✅ "Model loaded" message
- ✅ Signals start generating

### **First 30 Minutes:**
- ✅ First trade appears
- ✅ Confidence level ~0.40-0.65
- ✅ Direction (BUY or SELL)
- ✅ No errors in logs

### **First Hour:**
- ✅ 1-3 trades
- ✅ Both BUY and SELL (ideally)
- ✅ Confidence levels consistent
- ✅ Win rate tracking

---

## 🎯 MONITORING DASHBOARD

The real-time monitor shows:

### **1. Trade Status:**
```
📈 TRADE STATUS
Trades in last hour: 3
   BUY: 2, SELL: 1
   P&L: $+12.50
   Win Rate: 66.7%

Last 3 Trades:
   17:45:23 | BUY  | $+5.20
   17:52:10 | SELL | $+7.30
   17:58:45 | BUY  | $-2.10
```

### **2. Confidence Levels:**
```
🎯 CONFIDENCE LEVELS
Recent Predictions (last 20 signals):
   Min: -0.5234
   Max: +0.6123
   Mean: +0.1245
   Abs Max: 0.6123

   Above 0.40 threshold: 8/20
   UP: 12, DOWN: 8

   Latest: +0.4567 (UP)
   ✅ TRADEABLE (above 0.40)
```

### **3. System Status:**
```
🤖 SYSTEM STATUS
Bot Process: ✅ RUNNING
Config CONF_MIN: 0.40
Model: New (64.95% accuracy)
```

---

## ✅ SUCCESS INDICATORS

**Bot is WORKING if you see:**
1. ✅ Confidence levels ranging 0.30-0.70
2. ✅ Some predictions above 0.40
3. ✅ Both UP and DOWN predictions
4. ✅ Trades executing when confidence > 0.40
5. ✅ No errors in logs

**Bot is NOT working if:**
1. ❌ All confidence levels < 0.30
2. ❌ No predictions above 0.40
3. ❌ Only UP or only DOWN predictions
4. ❌ No trades after 1 hour
5. ❌ Errors in logs

---

## 📋 MONITORING CHECKLIST

**After Restart:**

**5 Minutes:**
- [ ] Bot started successfully
- [ ] No startup errors
- [ ] Signals generating

**30 Minutes:**
- [ ] First trade executed
- [ ] Confidence ~0.40-0.65
- [ ] Trade direction noted

**1 Hour:**
- [ ] 1-3 trades total
- [ ] Both BUY and SELL (ideally)
- [ ] Win rate >40%
- [ ] P&L tracked

**6 Hours:**
- [ ] 5-10 trades total
- [ ] Win rate >50%
- [ ] P&L positive
- [ ] Both directions confirmed

---

## 🚨 TROUBLESHOOTING

### **If no trades after 30 minutes:**
1. Check monitor: Are predictions above 0.40?
2. If yes but no trades: Check bot logs for errors
3. If no: Market may be unclear (wait longer)

### **If only BUY or only SELL:**
1. Check predictions: Are they one-directional?
2. If yes: Model issue (may need retraining)
3. If no: Configuration issue

### **If errors in logs:**
1. Note the error message
2. Check if bot is still running
3. May need to fix and restart

---

## 📊 EXPECTED PERFORMANCE

**With CONF_MIN = 0.40:**

| Timeframe | Expected Trades | Expected Win Rate | Expected P&L |
|-----------|----------------|-------------------|--------------|
| 30 min | 0-1 | N/A | N/A |
| 1 hour | 1-3 | 40-60% | $-10 to +$20 |
| 6 hours | 5-10 | 50-55% | $+10 to +$50 |
| 24 hours | 10-20 | 50-60% | $+20 to +$100 |

---

## 🎯 COMMANDS SUMMARY

**Stop current bot:**
- Press Ctrl+C in bot terminal

**Start new bot:**
```powershell
python run_5m_debug.py
```

**Start monitor (new terminal):**
```powershell
python monitor_5m_realtime.py
```

**Quick status check:**
```powershell
python -c "import pandas as pd; from datetime import datetime, timedelta; df=pd.read_csv('paper_trading_outputs/executions_paper.csv'); df['ts_ist']=pd.to_datetime(df['ts_ist']); recent=df[df['ts_ist']>datetime.now()-timedelta(hours=1)]; print(f'Trades: {len(recent)}'); print(f'BUY: {sum(recent.side==\"BUY\")}'); print(f'SELL: {sum(recent.side==\"SELL\")}')"
```

---

## ✅ READY TO RESTART!

**Current Status:**
- ✅ Config updated (CONF_MIN = 0.40)
- ✅ Monitor script ready
- ✅ Model deployed (64.95% accuracy)
- ⏳ Waiting for restart

**Next Steps:**
1. Stop current bot (Ctrl+C)
2. Start new bot (`python run_5m_debug.py`)
3. Start monitor in new terminal (`python monitor_5m_realtime.py`)
4. Watch for first trade (30 min)

---

**Let's restart and start trading!** 🚀
