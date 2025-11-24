"""
Custom model classes ported from the training notebook so saved joblib artifacts
can be unpickled in the live runtime. These implementations match the notebook
semantics but include explicit imports to avoid relying on notebook globals.
"""

from __future__ import annotations

import numpy as np
from sklearn.base import clone
from sklearn.metrics import accuracy_score
from sklearn.isotonic import IsotonicRegression


class EnhancedMetaClassifier:
    """Enhanced Meta-Learner for 3-class classification.

    Notes:
    - Replicates the notebook implementation with explicit imports.
    - Stacks multiple base models and trains a logistic regression meta-model
      on out-of-fold base probabilities with purged time splits.
    """

    def __init__(
        self,
        meta_C: float = 1.0,
        random_state: int = 42,
        n_folds: int = 5,
        embargo_pct: float = 0.01,
        purge_pct: float = 0.02,
        min_train_samples: int = 1000,
        n_classes: int = 3,
    ) -> None:
        # Lazy imports inside methods in the notebook are made explicit where needed.
        from sklearn.preprocessing import RobustScaler

        self.meta_C = meta_C
        self.random_state = random_state
        self.n_folds = n_folds
        self.embargo_pct = embargo_pct
        self.purge_pct = purge_pct
        self.min_train_samples = min_train_samples
        self.n_classes = n_classes

        self.base_models = {}
        self.meta_model = None
        self.scaler = RobustScaler()
        self.is_fitted = False
        self.meta_score = 0.0
        self.cv_scores = {}
        self.fold_scores = {}

    def get_params(self, deep: bool = True):  # sklearn API requires 'deep'
        _ = deep  # referenced to satisfy linters
        return {
            "meta_C": self.meta_C,
            "random_state": self.random_state,
            "n_folds": self.n_folds,
            "embargo_pct": self.embargo_pct,
            "purge_pct": self.purge_pct,
            "min_train_samples": self.min_train_samples,
            "n_classes": self.n_classes,
        }

    def set_params(self, **params):
        for param, value in params.items():
            if hasattr(self, param):
                setattr(self, param, value)
            else:
                raise ValueError(
                    f"Invalid parameter {param} for estimator {type(self).__name__}"
                )
        return self

    def _get_base_models(self):
        from sklearn.preprocessing import QuantileTransformer, RobustScaler
        from sklearn.ensemble import (
            ExtraTreesClassifier,
            GradientBoostingClassifier,
            HistGradientBoostingClassifier,
            RandomForestClassifier,
        )
        from sklearn.naive_bayes import GaussianNB
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline

        return {
            "histgb": HistGradientBoostingClassifier(
                max_iter=180,
                learning_rate=0.07,
                max_depth=7,
                min_samples_leaf=20,
                l2_regularization=1e-2,
                max_bins=255,
                validation_fraction=0.1,
                random_state=self.random_state,
            ),
            "randomforest": RandomForestClassifier(
                n_estimators=300,
                max_depth=16,
                min_samples_split=4,
                min_samples_leaf=2,
                max_features="sqrt",
                bootstrap=True,
                class_weight="balanced_subsample",
                random_state=self.random_state,
                n_jobs=-1,
            ),
            "extratrees": ExtraTreesClassifier(
                n_estimators=300,
                max_depth=16,
                min_samples_split=4,
                min_samples_leaf=2,
                class_weight="balanced",
                random_state=self.random_state,
                n_jobs=-1,
            ),
            "gb_classifier": GradientBoostingClassifier(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=3,
                subsample=0.7,
                random_state=self.random_state,
            ),
            "logistic_scaled": Pipeline(
                [
                    (
                        "quantile",
                        QuantileTransformer(
                            n_quantiles=800, output_distribution="normal"
                        ),
                    ),
                    ("scaler", RobustScaler()),
                    (
                        "classifier",
                        LogisticRegression(
                            random_state=self.random_state,
                            max_iter=1500,
                            C=1.0,
                            solver="lbfgs",
                            multi_class="auto",
                            class_weight="balanced",
                        ),
                    ),
                ]
            ),
            "naive_bayes_scaled": Pipeline(
                [("scaler", RobustScaler()), ("classifier", GaussianNB())]
            ),
        }

    def _create_purged_splits(self, X, y):
        n_samples = len(X)
        embargo_periods = max(1, int(n_samples * self.embargo_pct))
        purge_periods = max(1, int(n_samples * self.purge_pct))

    # class_counts = y.value_counts()  # Not used downstream; retain logic but avoid unused var

        min_required_samples = (
            self.min_train_samples + embargo_periods + purge_periods + 100
        )
        if n_samples < min_required_samples:
            raise ValueError(
                f"INSUFFICIENT DATA: Need at least {min_required_samples} samples for purged CV, got {n_samples}"
            )

        splits = []
        step_size = n_samples // (self.n_folds + 1)

        for i in range(self.n_folds):
            train_end = (i + 1) * step_size
            train_start = 0

            train_end_purged = max(
                train_start + self.min_train_samples, train_end - purge_periods
            )

            val_start = train_end + embargo_periods
            val_end = min(val_start + step_size, n_samples)

            train_size = train_end_purged - train_start
            val_size = val_end - val_start

            if train_size >= self.min_train_samples and val_size >= 50:
                train_idx = list(range(train_start, train_end_purged))
                val_idx = list(range(val_start, val_end))

                # Basic class coverage checks
                try:
<<<<<<< HEAD
                    train_classes = np.unique(y.iloc[train_idx])
                    val_classes = np.unique(y.iloc[val_idx])
=======
                    import numpy as _np

                    train_classes = _np.unique(y.iloc[train_idx])
                    val_classes = _np.unique(y.iloc[val_idx])
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde
                    if len(train_classes) < 2 or len(val_classes) < 2:
                        continue
                except (ValueError, RuntimeError):
                    pass

                # Time overlap guard when X has an index
                if hasattr(X, "index"):
                    try:
                        train_times = X.index[train_idx]
                        val_times = X.index[val_idx]
                        if len(train_times) > 0 and len(val_times) > 0:
                            train_max_time = max(train_times)
                            val_min_time = min(val_times)
                            if train_max_time >= val_min_time:
                                continue
                    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
                        pass

                splits.append((train_idx, val_idx))

        if len(splits) == 0:
            raise ValueError("No valid classification splits created")
        if len(splits) < 2:
            raise ValueError("Only {len(splits)} valid folds created, need at least 2")
        return splits

    def fit(self, X, y):
        from sklearn.linear_model import LogisticRegression

<<<<<<< HEAD
        unique_classes = np.unique(y)
=======
        import numpy as _np

        unique_classes = _np.unique(y)
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde
        if len(unique_classes) < 2:
            raise ValueError(
                f"Need at least 2 classes for classification, found: {unique_classes}"
            )

        self.base_models = self._get_base_models()
        purged_splits = self._create_purged_splits(X, y)

        oof_probs = np.zeros((len(X), len(self.base_models) * self.n_classes))

        for model_idx, (name, model) in enumerate(self.base_models.items()):
            fold_scores = []

            for _, (train_idx, val_idx) in enumerate(purged_splits):
                # Guard against time overlap when using time index
                if hasattr(X, "index") and len(X.index) > 0:
                    try:
                        train_max_time = X.index[train_idx].max()
                        val_min_time = X.index[val_idx].min()
                        if train_max_time >= val_min_time:
                            continue
                    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
                        pass

                X_train_fold, X_val_fold = X.iloc[train_idx], X.iloc[val_idx]
                y_train_fold, y_val_fold = y.iloc[train_idx], y.iloc[val_idx]

                model_clone = clone(model)
                try:
                    model_clone.fit(X_train_fold, y_train_fold)
                    val_probs = model_clone.predict_proba(X_val_fold)

                    prob_start = model_idx * self.n_classes
                    prob_end = prob_start + self.n_classes

                    if val_probs.shape[1] == self.n_classes:
                        oof_probs[val_idx, prob_start:prob_end] = val_probs
                    else:
<<<<<<< HEAD
                        temp_probs = np.zeros((len(val_idx), self.n_classes))
                        classes = getattr(model_clone, "classes_", list(range(val_probs.shape[1])))
=======
                        temp_probs = _np.zeros((len(val_idx), self.n_classes))
                        classes = getattr(
                            model_clone, "classes_", list(range(val_probs.shape[1]))
                        )
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde
                        for i, cls in enumerate(classes):
                            if cls < self.n_classes:
                                temp_probs[:, cls] = val_probs[:, i]
                        oof_probs[val_idx, prob_start:prob_end] = temp_probs

                    fold_accuracy = accuracy_score(
<<<<<<< HEAD
                        y_val_fold, np.argmax(val_probs, axis=1) if val_probs.shape[1] == self.n_classes else y_val_fold
=======
                        y_val_fold,
                        (
                            _np.argmax(val_probs, axis=1)
                            if val_probs.shape[1] == self.n_classes
                            else y_val_fold
                        ),
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde
                    )
                    fold_scores.append(fold_accuracy)

                except (ValueError, RuntimeError, TypeError):
                    # Fallback: uniform probs
                    prob_start = model_idx * self.n_classes
                    prob_end = prob_start + self.n_classes
                    oof_probs[val_idx, prob_start:prob_end] = 1.0 / self.n_classes
                    fold_scores.append(0.0)

            self.cv_scores[name] = float(np.mean(fold_scores)) if fold_scores else 0.0
            self.fold_scores[name] = fold_scores

        # Fit meta logistic on stacked probabilities
        oof_probs_scaled = self.scaler.fit_transform(oof_probs)
        self.meta_model = LogisticRegression(
            C=self.meta_C,
            random_state=self.random_state,
            max_iter=1500,
            solver="lbfgs",
            multi_class="auto",
            class_weight="balanced",
        )
        self.meta_model.fit(oof_probs_scaled, y)

        meta_pred = self.meta_model.predict(oof_probs_scaled)
        self.meta_score = accuracy_score(y, meta_pred)

        # Fit base models on full data for inference
        for _, model in self.base_models.items():
            model.fit(X, y)

        self.is_fitted = True
        return self

    def predict(self, X):
        if not self.is_fitted:
            return np.zeros(len(X))
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)

    def predict_proba(self, X):
        if not self.is_fitted:
            return np.full((len(X), self.n_classes), 1.0 / self.n_classes)

        base_probs = np.zeros((len(X), len(self.base_models) * self.n_classes))

        for model_idx, (_, model) in enumerate(self.base_models.items()):
            try:
                model_probs = model.predict_proba(X)
                prob_start = model_idx * self.n_classes
                prob_end = prob_start + self.n_classes

                if model_probs.shape[1] == self.n_classes:
                    base_probs[:, prob_start:prob_end] = model_probs
                else:
                    temp_probs = np.zeros((len(X), self.n_classes))
                    classes = getattr(
                        model, "classes_", list(range(model_probs.shape[1]))
                    )
                    for i, cls in enumerate(classes):
                        if cls < self.n_classes:
                            temp_probs[:, cls] = model_probs[:, i]
                    base_probs[:, prob_start:prob_end] = temp_probs

            except (ValueError, RuntimeError, TypeError):
                prob_start = model_idx * self.n_classes
                prob_end = prob_start + self.n_classes
                base_probs[:, prob_start:prob_end] = 1.0 / self.n_classes

        base_probs_scaled = self.scaler.transform(base_probs)
        return self.meta_model.predict_proba(base_probs_scaled)

    def get_model_info(self):
        if not self.is_fitted:
            return {"type": "enhanced_meta_classifier", "fitted": False}

        feature_importance = {}
        model_names = list(self.base_models.keys())

        for class_idx in range(self.n_classes):
            feature_importance[f"class_{class_idx}"] = {}
            for model_idx, name in enumerate(model_names):
                prob_indices = list(
                    range(model_idx * self.n_classes, (model_idx + 1) * self.n_classes)
                )
                coefs = (
                    self.meta_model.coef_[class_idx]
                    if self.n_classes > 2
                    else self.meta_model.coef_[0]
                )
                feature_importance[f"class_{class_idx}"][name] = float(
                    np.mean(np.abs(coefs[prob_indices]))
                )

        return {
            "type": "enhanced_meta_classifier",
            "fitted": True,
            "meta_score": float(self.meta_score),
            "feature_importance": feature_importance,
            "meta_C": self.meta_C,
            "cv_scores": self.cv_scores,
            "fold_scores": self.fold_scores,
            "n_folds": self.n_folds,
            "embargo_pct": self.embargo_pct,
            "purge_pct": self.purge_pct,
            "n_classes": self.n_classes,
        }


class CustomClassificationCalibrator:
    """Isotonic-only calibration for the meta-learner (fits on calibration window)."""

    def __init__(self, base_estimator):
        self.base_estimator = base_estimator
        self.calibrators = {}
        self.is_fitted = False

    def fit(self, X, y):
        # Get uncalibrated probabilities from the already-fitted base estimator
        uncal_probas = self.base_estimator.predict_proba(X)
        n_classes = uncal_probas.shape[1]
        y_arr = np.asarray(y)

        for class_idx in range(n_classes):
            class_probas = uncal_probas[:, class_idx]
            class_labels = (y_arr == class_idx).astype(int)

            # Isotonic requires both positive and negative examples; fallback if class absent
            pos = int(class_labels.sum())
            neg = int(len(class_labels) - pos)
            if pos == 0 or neg == 0:
                # Not enough signal to fit isotonic; keep calibrator as None to pass through uncalibrated probs
                self.calibrators[class_idx] = None
                continue

            calibrator = IsotonicRegression(out_of_bounds="clip")
            calibrator.fit(class_probas, class_labels)
            self.calibrators[class_idx] = calibrator

        self.is_fitted = True
        return self

    def predict_proba(self, X):
        if not self.is_fitted:
            raise ValueError("Calibrator must be fitted before making predictions")

        uncal_probas = self.base_estimator.predict_proba(X)
        cal_probas = uncal_probas.copy()

        n_classes = uncal_probas.shape[1]
        for class_idx in range(n_classes):
            calibrator = self.calibrators.get(class_idx, None)
            if calibrator is not None:
<<<<<<< HEAD
                cal_probas[:, class_idx] = calibrator.transform(uncal_probas[:, class_idx])
            # else: leave uncalibrated values as-is
=======
                cal_probas[:, class_idx] = calibrator.transform(
                    uncal_probas[:, class_idx]
                )
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde

        # Normalize rows to sum to 1 to get a proper probability distribution
        row_sums = cal_probas.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        cal_probas = cal_probas / row_sums
        return cal_probas

    def predict(self, X):
        probas = self.predict_proba(X)
        return np.argmax(probas, axis=1)
