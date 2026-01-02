"""
COMPREHENSIVE ALL TIMEFRAMES MODEL STATUS
Analyze 5m, 1h, 12h, and 24h models
"""
import json
import os
from datetime import datetime

print("=" * 100)
print("ALL TIMEFRAMES MODEL STATUS - COMPREHENSIVE ANALYSIS")
print("=" * 100)
print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

timeframes = {
    '5m': {
        'dir': 'live_demo',
        'latest': 'live_demo/models/LATEST.json'
    },
    '1h': {
        'dir': 'live_demo_1h',
        'latest': 'live_demo_1h/models/LATEST.json'
    },
    '12h': {
        'dir': 'live_demo_12h',
        'latest': 'live_demo_12h/models/LATEST.json'
    },
    '24h': {
        'dir': 'live_demo_24h',
        'latest': 'live_demo_24h/models/LATEST.json'
    }
}

results = {}

# ============================================
# ANALYZE EACH TIMEFRAME
# ============================================

for tf, paths in timeframes.items():
    print(f"{'=' * 100}")
    print(f"TIMEFRAME: {tf.upper()}")
    print(f"{'=' * 100}")
    print()
    
    result = {
        'timeframe': tf,
        'has_model': False,
        'model_date': None,
        'age_days': None,
        'accuracy': None,
        'samples': None,
        'target': None,
        'features': None,
        'file_size_mb': None,
        'status': 'Unknown'
    }
    
    if os.path.exists(paths['latest']):
        print(f"✅ Model directory exists: {paths['dir']}/models/")
        
        try:
            # Load LATEST.json
            with open(paths['latest'], 'r') as f:
                latest = json.load(f)
            
            print(f"✅ LATEST.json found")
            print()
            
            # Get model filename
            meta_classifier = latest.get('meta_classifier', '')
            calibrator = latest.get('calibrator', '')
            
            print(f"Model Files:")
            print(f"  Meta-classifier: {meta_classifier}")
            print(f"  Calibrator: {calibrator}")
            print()
            
            # Extract date from filename
            try:
                date_str = meta_classifier.split('_')[2]
                if len(date_str) == 8:  # YYYYMMDD
                    model_date = datetime.strptime(date_str, '%Y%m%d')
                elif len(date_str) == 15:  # YYYYMMDD_HHMMSS
                    model_date = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                else:
                    model_date = None
                
                if model_date:
                    age_days = (datetime.now() - model_date).days
                    result['model_date'] = model_date.strftime('%Y-%m-%d')
                    result['age_days'] = age_days
                    print(f"Training Date: {model_date.strftime('%Y-%m-%d')}")
                    print(f"Model Age: {age_days} days")
            except:
                print("⚠️ Could not extract date from filename")
            
            print()
            
            # Load metadata
            meta_file = f"{paths['dir']}/models/{latest['training_meta']}"
            if os.path.exists(meta_file):
                with open(meta_file, 'r') as f:
                    meta = json.load(f)
                
                # Extract metrics (handle different formats)
                accuracy = meta.get('meta_score_in_sample', meta.get('calibrated_score', 0))
                samples = meta.get('training_samples', meta.get('train_rows', 0))
                target = meta.get('target', meta.get('classification_target', 'N/A'))
                features = meta.get('n_features', len(meta.get('feature_cols', [])) if 'feature_cols' in meta else 0)
                
                result['accuracy'] = accuracy
                result['samples'] = samples
                result['target'] = target
                result['features'] = features
                
                print(f"Performance:")
                print(f"  Training Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
                print(f"  Training Samples: {samples:,}")
                print(f"  Target: {target}")
                print(f"  Features: {features}")
                print()
                
                # Get file size
                cal_path = f"{paths['dir']}/models/{calibrator}"
                if os.path.exists(cal_path):
                    size_bytes = os.path.getsize(cal_path)
                    size_mb = size_bytes / (1024 * 1024)
                    result['file_size_mb'] = size_mb
                    print(f"Model Size: {size_mb:.2f} MB")
                print()
                
                # Assessment
                issues = []
                
                if age_days and age_days > 90:
                    issues.append(f"Very old ({age_days} days)")
                elif age_days and age_days > 60:
                    issues.append(f"Getting old ({age_days} days)")
                
                if samples < 500:
                    issues.append(f"Very few samples ({samples:,})")
                elif samples < 1000:
                    issues.append(f"Limited samples ({samples:,})")
                
                if accuracy < 0.50:
                    issues.append(f"Low accuracy ({accuracy*100:.1f}%)")
                elif accuracy < 0.60:
                    issues.append(f"Moderate accuracy ({accuracy*100:.1f}%)")
                
                if features != 17:
                    issues.append(f"Feature mismatch (expected 17, got {features})")
                
                if issues:
                    print("⚠️ Issues:")
                    for issue in issues:
                        print(f"  - {issue}")
                    result['status'] = 'Needs Improvement'
                else:
                    print("✅ Status: Good")
                    result['status'] = 'Good'
                
                result['has_model'] = True
                
            else:
                print("❌ Metadata file not found")
                result['status'] = 'Incomplete'
            
        except Exception as e:
            print(f"❌ Error analyzing {tf}: {e}")
            result['status'] = 'Error'
    else:
        print(f"❌ No model directory found: {paths['dir']}/models/")
        result['status'] = 'No Model'
    
    results[tf] = result
    print()

# ============================================
# SUMMARY TABLE
# ============================================

print("=" * 100)
print("SUMMARY TABLE - ALL TIMEFRAMES")
print("=" * 100)
print()

# Header
print(f"{'TF':>4s} | {'Has Model':>10s} | {'Age (days)':>11s} | {'Accuracy':>10s} | {'Samples':>10s} | {'Features':>8s} | {'Status':>20s}")
print("-" * 100)

# Rows
for tf in ['5m', '1h', '12h', '24h']:
    r = results[tf]
    
    has = "✅ Yes" if r['has_model'] else "❌ No"
    age = str(r['age_days']) if r['age_days'] is not None else 'N/A'
    acc = f"{r['accuracy']*100:.2f}%" if r['accuracy'] is not None else 'N/A'
    samp = f"{r['samples']:,}" if r['samples'] is not None else 'N/A'
    feat = str(r['features']) if r['features'] is not None else 'N/A'
    status = r['status']
    
    print(f"{tf:>4s} | {has:>10s} | {age:>11s} | {acc:>10s} | {samp:>10s} | {feat:>8s} | {status:>20s}")

print()

# ============================================
# DETAILED COMPARISON
# ============================================

print("=" * 100)
print("DETAILED COMPARISON")
print("=" * 100)
print()

# Best model
best_tf = None
best_score = 0

for tf, r in results.items():
    if r['has_model'] and r['accuracy'] is not None:
        # Score based on: accuracy, samples, freshness
        score = 0
        score += r['accuracy'] * 100  # Accuracy weight
        score += min(r['samples'] / 1000, 10) * 10  # Sample weight (capped)
        if r['age_days'] is not None:
            score -= r['age_days'] / 10  # Age penalty
        
        if score > best_score:
            best_score = score
            best_tf = tf

if best_tf:
    print(f"🏆 BEST MODEL: {best_tf.upper()}")
    r = results[best_tf]
    print(f"   Accuracy: {r['accuracy']*100:.2f}%")
    print(f"   Samples: {r['samples']:,}")
    print(f"   Age: {r['age_days']} days")
    print()

# Models needing attention
print("Models Needing Attention:")
print()

needs_attention = []

for tf, r in results.items():
    if not r['has_model']:
        needs_attention.append((tf, "🔴 CRITICAL", "No model exists"))
    elif r['samples'] and r['samples'] < 500:
        needs_attention.append((tf, "🔴 CRITICAL", f"Very few samples ({r['samples']:,})"))
    elif r['samples'] and r['samples'] < 1000:
        needs_attention.append((tf, "🟡 WARNING", f"Limited samples ({r['samples']:,})"))
    elif r['age_days'] and r['age_days'] > 90:
        needs_attention.append((tf, "🟡 WARNING", f"Very old ({r['age_days']} days)"))

if needs_attention:
    for tf, severity, reason in needs_attention:
        print(f"  {severity} {tf.upper()}: {reason}")
else:
    print("  ✅ All models are in good condition")

print()

# ============================================
# RECOMMENDATIONS
# ============================================

print("=" * 100)
print("RECOMMENDATIONS")
print("=" * 100)
print()

print("Priority Order for Action:")
print()

# Determine priorities
priorities = []

for tf, r in results.items():
    if not r['has_model']:
        priorities.append((1, tf, "Create new model (no model exists)"))
    elif r['samples'] and r['samples'] < 500:
        priorities.append((2, tf, f"Retrain urgently (only {r['samples']:,} samples)"))
    elif r['samples'] and r['samples'] < 1000:
        priorities.append((3, tf, f"Retrain soon (limited {r['samples']:,} samples)"))
    elif r['age_days'] and r['age_days'] > 90:
        priorities.append((4, tf, f"Retrain when convenient ({r['age_days']} days old)"))

priorities.sort(key=lambda x: x[0])

for i, (priority, tf, reason) in enumerate(priorities, 1):
    priority_label = ["🔴 HIGH", "🟡 MEDIUM", "🟢 LOW"][min(priority-1, 2)]
    print(f"{i}. {priority_label} - {tf.upper()}: {reason}")

if not priorities:
    print("✅ No immediate action needed for any timeframe")

print()

# ============================================
# FINAL SUMMARY
# ============================================

print("=" * 100)
print("FINAL SUMMARY")
print("=" * 100)
print()

models_with_own = sum(1 for r in results.values() if r['has_model'])
models_good = sum(1 for r in results.values() if r['status'] == 'Good')
models_need_work = sum(1 for r in results.values() if r['status'] in ['Needs Improvement', 'Incomplete'])
models_missing = sum(1 for r in results.values() if r['status'] == 'No Model')

print(f"Total Timeframes: 4 (5m, 1h, 12h, 24h)")
print(f"Models with own model: {models_with_own}/4")
print(f"Models in good condition: {models_good}/4")
print(f"Models needing work: {models_need_work}/4")
print(f"Models missing: {models_missing}/4")
print()

if models_good == 4:
    print("🎉 EXCELLENT: All timeframes have good models!")
elif models_with_own == 4:
    print("✅ GOOD: All timeframes have models, some need improvement")
else:
    print("⚠️ ATTENTION NEEDED: Some timeframes missing models or need work")

print()
print("=" * 100)
