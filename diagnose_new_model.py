import joblib
import sys
sys.path.insert(0, r'c:\Users\yashw\MetaStackerBandit')

# Load the new model
new_model_path = r"c:\Users\yashw\MetaStackerBandit\live_demo\models\meta_classifier_20260102_111331_d7a9e9fb3a42.joblib"
new_model = joblib.load(new_model_path)

print("Model type: {0}".format(type(new_model).__name__))
print("Model class: {0}".format(type(new_model)))

# If it's LogisticRegression, check its attributes
if hasattr(new_model, 'coef_'):
    print("\nModel coefficients shape: {0}".format(new_model.coef_.shape))
    print("Number of features (from coef_): {0}".format(new_model.coef_.shape[1]))
    
if hasattr(new_model, 'n_features_in_'):
    print("n_features_in_: {0}".format(new_model.n_features_in_))

# Check if there's an intercept
if hasattr(new_model, 'intercept_'):
    print("Has intercept: Yes")
    print("Intercept shape: {0}".format(new_model.intercept_.shape))

# This appears to be the WRONG model - it's the meta-model, not the full EnhancedMetaClassifier
print("\n" + "=" * 80)
print("DIAGNOSIS:")
print("=" * 80)
print("The saved model is a LogisticRegression, not an EnhancedMetaClassifier.")
print("This is likely the INNER meta-model that was accidentally saved.")
print("The meta-model expects 18 features because it takes stacked probabilities")
print("from 6 base models (6 models * 3 classes = 18 probability features).")
print("\nSOLUTION: The training notebook needs to save the full EnhancedMetaClassifier,")
print("not just the inner meta_model attribute.")
