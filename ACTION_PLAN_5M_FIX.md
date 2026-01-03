# ACTION PLAN: Fix 5M Model and Retrain Properly

## Current Situation
✗ **Old Model (Oct 2025)**: Works but has issues (low accuracy, stale)
✗ **New Model (Jan 2026)**: Broken - saved incorrectly, expects 18 features instead of 17
✗ **Bot Status**: Currently reverted to old model (temporary fix)

## Root Cause Analysis

### The Bug in retrain_5m_automated.py
**Line 396:**
```python
joblib.dump(meta_classifier, f"{MODEL_DIR}/{meta_file}")  # ✗ WRONG!
```

This saves only the `LogisticRegression` meta-classifier which:
- Expects 18 features (4 base models × 3 classes + 6 more = 18 stacked probabilities)
- Cannot process the 17 raw features from live trading
- Causes the "expecting 18 features" error

### What Should Be Saved
A wrapper object that:
- Accepts 17 raw features ✓
- Runs base models internally
- Stacks their predictions
- Feeds to meta-classifier
- Returns final probabilities

## Solution Options

### Option 1: Quick Fix - Use Old Model (CURRENT STATUS)
**Status**: ✓ DONE
**Pros**: Bot runs immediately
**Cons**: Old model issues persist (low accuracy, stale data)
**Duration**: Temporary until proper fix

### Option 2: Retrain with Fixed Script (RECOMMENDED)
**Status**: ⏳ TODO
**Steps**:
1. Fix `retrain_5m_automated.py` with SimpleMetaClassifier wrapper
2. Retrain model with fresh data
3. Validate new model
4. Deploy and monitor

**Pros**: 
- Fresh model with recent data
- Properly saved structure
- Long-term solution

**Cons**: 
- Requires retraining time (~10-30 minutes)
- Need to validate performance

### Option 3: Try to Fix Existing January Model
**Status**: ⏳ POSSIBLE
**Approach**: Load the January meta_classifier and wrap it with base models
**Challenge**: We don't have the base models from January training saved separately

## RECOMMENDED ACTION PLAN

### Phase 1: Immediate (NOW)
✓ **DONE**: Reverted to October model to keep bot running
✓ **DONE**: Identified the bug in retraining script
✓ **DONE**: Created fix documentation

### Phase 2: Fix and Retrain (NEXT)
1. **Update retrain_5m_automated.py**:
   - Add `SimpleMetaClassifier` wrapper class
   - Change line 396 to save the wrapper instead of just meta_classifier
   
2. **Run Retraining**:
   ```bash
   python retrain_5m_automated.py
   ```
   
3. **Validate New Model**:
   - Check it accepts 17 features
   - Verify accuracy > 55%
   - Test inference works

4. **Deploy**:
   - New model will auto-update LATEST.json
   - Restart bot
   - Monitor for 24-48 hours

### Phase 3: Monitor and Optimize (ONGOING)
- Track win rate, P&L
- Compare vs old model performance
- Adjust if needed

## Files to Modify

### 1. retrain_5m_automated.py
**Add after line 32:**
```python
class SimpleMetaClassifier:
    def __init__(self, base_models, meta_model, feature_columns):
        self.base_models = base_models
        self.meta_model = meta_model
        self.feature_columns = feature_columns
        self.is_fitted = True
        
    def predict_proba(self, X):
        meta_features = []
        for name, model in self.base_models.items():
            pred = model.predict_proba(X)
            meta_features.append(pred)
        X_meta = np.hstack(meta_features)
        return self.meta_model.predict_proba(X_meta)
    
    def predict(self, X):
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)
```

**Replace lines 394-397:**
```python
# Create wrapper that includes base models
print("Creating model wrapper...")
full_model = SimpleMetaClassifier(
    base_models=trained_models,
    meta_model=meta_classifier,
    feature_columns=feature_columns
)

# Save the FULL model (not just meta_classifier)
meta_file = f'meta_classifier_{timestamp}_{schema_hash}.joblib'
joblib.dump(full_model, f"{MODEL_DIR}/{meta_file}")
print(f"✅ Saved: {meta_file} (full model with base estimators)")
```

## Testing the Fix

After retraining, test with:
```bash
python test_model_fix.py
```

Should see:
```
✓ SUCCESS! Inference completed without errors.
FIX VERIFIED - Model is working correctly!
```

## Rollback Plan

If new model has issues:
```bash
# Revert to October 2025 model (current backup)
# Already in: live_demo/models/backup/backup_YYYYMMDD_HHMMSS/
```

## Summary

**Current State**: Bot running on old model (temporary)
**Next Step**: Fix retraining script and retrain
**Expected Outcome**: Fresh, properly-saved model that works correctly
**Timeline**: ~30-60 minutes to fix, retrain, and deploy

---

**Ready to proceed with Phase 2?**
