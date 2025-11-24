"""
Reproducibility and Configuration Tracking for MetaStackerBandit
Tracks model versions, git commits, training metadata, and configuration hashes
"""

import hashlib
import json
import subprocess
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import pytz
from dataclasses import dataclass, asdict
import pickle

IST = pytz.timezone("Asia/Kolkata")


@dataclass
class ReproConfig:
    """Reproducibility configuration container"""

    git_sha: Optional[str] = None
    model_version: Optional[str] = None
    feature_version: Optional[str] = None
    seed: Optional[int] = None
    train_start_ist: Optional[str] = None
    train_end_ist: Optional[str] = None
    hyperparams_hash: Optional[str] = None
    data_hash: Optional[str] = None
    adv_method: Optional[str] = None


class ReproTracker:
    """Reproducibility and configuration tracking system"""

    def __init__(self, model_path: str = "live_demo/models/LATEST.json"):
        self.model_path = model_path
        self.config_cache = {}
        self._load_existing_config()

    def _load_existing_config(self):
        """Load existing configuration from model manifest"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, "r") as f:
                    manifest = json.load(f)
                    self.config_cache = manifest.get("repro_config", {})
        except Exception:
            self.config_cache = {}

    def get_git_sha(self) -> Optional[str]:
        """Get current git commit SHA"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
            )
            if result.returncode == 0:
                return result.stdout.strip()[:7]  # Short SHA
        except Exception:
            pass
        return None

    def get_model_version(self) -> Optional[str]:
        """Get model version from manifest"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, "r") as f:
                    manifest = json.load(f)
                    return manifest.get("model_version", None)
        except Exception:
            pass
        return None

    def get_feature_version(self) -> Optional[str]:
        """Get feature version from feature schema"""
        try:
            # Try to get from feature columns file
            feature_file = (
                "live_demo/models/feature_columns_20251018_101628_d7a9e9fb3a42.json"
            )
            if os.path.exists(feature_file):
                with open(feature_file, "r") as f:
                    feature_data = json.load(f)
                    return feature_data.get("version", "v3.2.1")
        except Exception:
            pass
        return "v3.2.1"  # Default version

    def get_seed(self) -> Optional[int]:
        """Get random seed from configuration"""
        try:
            # Try to get from model manifest
            if os.path.exists(self.model_path):
                with open(self.model_path, "r") as f:
                    manifest = json.load(f)
                    return manifest.get("seed", 42)
        except Exception:
            pass
        return 42  # Default seed

    def get_training_dates(self) -> tuple[Optional[str], Optional[str]]:
        """Get training start and end dates"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, "r") as f:
                    manifest = json.load(f)
                    train_start = manifest.get(
                        "train_start", "2025-07-01T00:00:00+05:30"
                    )
                    train_end = manifest.get("train_end", "2025-09-30T23:59:59+05:30")
                    return train_start, train_end
        except Exception:
            pass
        return None, None

    def calculate_hyperparams_hash(self, hyperparams: Dict[str, Any]) -> str:
        """Calculate hash of hyperparameters"""
        # Sort keys for consistent hashing
        sorted_params = dict(sorted(hyperparams.items()))
        param_str = json.dumps(sorted_params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()[:8]

    def calculate_data_hash(self, data_paths: List[str]) -> str:
        """Calculate hash of training data"""
        combined_hash = hashlib.md5()

        for path in data_paths:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        combined_hash.update(chunk)

        return combined_hash.hexdigest()[:8]

    def get_adv_method(self) -> str:
        """Get ADV calculation method"""
        return "rolling_20d"  # Default method

    def get_current_config(self) -> ReproConfig:
        """Get current reproducibility configuration"""
        git_sha = self.get_git_sha()
        model_version = self.get_model_version()
        feature_version = self.get_feature_version()
        seed = self.get_seed()
        train_start, train_end = self.get_training_dates()
        adv_method = self.get_adv_method()

        # Get hyperparameters from model manifest
        hyperparams = {}
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, "r") as f:
                    manifest = json.load(f)
                    hyperparams = manifest.get("hyperparams", {})
        except Exception:
            pass

        hyperparams_hash = self.calculate_hyperparams_hash(hyperparams)

        # Get data hash from training data paths
        data_paths = [
            "live_demo/assets/top_cohort.csv",
            "live_demo/assets/bottom_cohort.csv",
            "paper_trading_outputs/models/weights_daily.csv"
        ]
        data_hash = self.calculate_data_hash(data_paths)

        return ReproConfig(
            git_sha=git_sha,
            model_version=model_version,
            feature_version=feature_version,
            seed=seed,
            train_start_ist=train_start,
            train_end_ist=train_end,
            hyperparams_hash=hyperparams_hash,
            data_hash=data_hash,
            adv_method=adv_method,
        )

    def log_repro_config(self, timestamp: float) -> Dict[str, Any]:
        """Log reproducibility configuration"""
        config = self.get_current_config()

        repro_log = {
            "ts_ist": datetime.fromtimestamp(timestamp / 1000, IST).isoformat(),
            "git_sha": config.git_sha,
            "model_version": config.model_version,
            "feature_version": config.feature_version,
            "seed": config.seed,
            "train_start_ist": config.train_start_ist,
            "train_end_ist": config.train_end_ist,
            "hyperparams_hash": config.hyperparams_hash,
            "data_hash": config.data_hash,
            "adv_method": config.adv_method,
        }

        return repro_log

    def save_config(self, config: ReproConfig):
        """Save configuration to cache"""
        self.config_cache = asdict(config)

        # Save to model manifest if it exists
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, "r") as f:
                    manifest = json.load(f)

                manifest["repro_config"] = self.config_cache

                with open(self.model_path, "w") as f:
                    json.dump(manifest, f, indent=2)
        except Exception:
            pass

    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary"""
        config = self.get_current_config()

        return {
            "git_sha": config.git_sha,
            "model_version": config.model_version,
            "feature_version": config.feature_version,
            "seed": config.seed,
            "training_period": f"{config.train_start_ist} to {config.train_end_ist}",
            "hyperparams_hash": config.hyperparams_hash,
            "data_hash": config.data_hash,
            "adv_method": config.adv_method,
            "reproducibility_score": self._calculate_repro_score(config),
        }

    def _calculate_repro_score(self, config: ReproConfig) -> float:
        """Calculate reproducibility score (0-1)"""
        score = 0.0
        total_fields = 9

        if config.git_sha:
            score += 1
        if config.model_version:
            score += 1
        if config.feature_version:
            score += 1
        if config.seed is not None:
            score += 1
        if config.train_start_ist:
            score += 1
        if config.train_end_ist:
            score += 1
        if config.hyperparams_hash:
            score += 1
        if config.data_hash:
            score += 1
        if config.adv_method:
            score += 1

        return score / total_fields

    def validate_reproducibility(self) -> Dict[str, Any]:
        """Validate reproducibility requirements"""
        config = self.get_current_config()

        validation = {
            "git_sha_present": config.git_sha is not None,
            "model_version_present": config.model_version is not None,
            "feature_version_present": config.feature_version is not None,
            "seed_present": config.seed is not None,
            "training_dates_present": config.train_start_ist is not None
            and config.train_end_ist is not None,
            "hyperparams_hash_present": config.hyperparams_hash is not None,
            "data_hash_present": config.data_hash is not None,
            "adv_method_present": config.adv_method is not None,
            "overall_score": self._calculate_repro_score(config),
        }

        validation["is_reproducible"] = validation["overall_score"] >= 0.8

        return validation
