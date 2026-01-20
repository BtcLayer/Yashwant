import os
import json
import hashlib
from datetime import datetime

class ManifestWriter:
    """Tracks run metadata and stream activity for run_manifest.json
    
    Adapted for 12h timeframe with appropriate update intervals.
    """
    
    def __init__(self, run_id: str, asset: str, output_dir: str, interval: str):
        self.run_id = run_id
        self.asset = asset
        self.output_dir = output_dir
        self.interval = interval
        self.manifest_path = os.path.join(output_dir, 'run_manifest.json')
        
        self.start_ts = None
        self.stream_counts = {}
        self.stream_last_ts = {}
        
        # Tracked streams for 12h bot (based on actual log streams)
        # These match the schema registry streams for 12h
        self.tracked_streams = [
            'signals',
            'calibration',
            'feature_log',
            'order_intent',
            'repro',
            'health',
            'executions',
            'costs',
            'pnl_equity',
            'ensemble',
            'overlay_status',
            'hyperliquid_fills'
        ]
        
        # Adaptive update intervals (in bars) - optimized for each timeframe
        # 12h bars are much slower, so we update less frequently
        self.update_intervals = {
            '5m': 50,    # ~4 hours (50 * 5min)
            '15m': 40,   # ~10 hours (40 * 15min)
            '1h': 24,    # ~1 day (24 * 1h)
            '12h': 7,    # ~3.5 days (7 * 12h) - appropriate for 12h timeframe
            '24h': 7     # ~1 week (7 * 24h)
        }
        self.update_interval = self.update_intervals.get(interval, 7)  # Default to 7 for 12h

    def _generate_hash(self, file_path: str) -> str:
        """Generate SHA256 hash of a file (first 16 chars)"""
        if not file_path or not os.path.exists(file_path):
            return "Not present"
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()[:16]
        except Exception:
            return "Error generating hash"

    def initialize(self, config_path: str = None, code_path: str = None, model_manifest_path: str = None):
        """Initialize the manifest file on disk"""
        self.start_ts = datetime.now().isoformat()
        
        # Use default code path (main.py) if not provided
        if not code_path:
            # This file is in live_demo_12h/ops/manifest_writer.py
            # Main is in live_demo_12h/main.py
            potential_paths = [
                os.path.join(os.path.dirname(__file__), '..', 'main.py'),
                os.path.join(os.path.dirname(__file__), '..', '..', 'live_demo_12h', 'main.py')
            ]
            for p in potential_paths:
                if os.path.exists(p):
                    code_path = p
                    break

        manifest = {
            "run_id": self.run_id,
            "asset": self.asset,
            "interval": self.interval,
            "start_ts": self.start_ts,
            "end_ts": self.start_ts,
            "stream_counts": self.stream_counts,
            "stream_last_ts": self.stream_last_ts,
            "cfg_hash": self._generate_hash(config_path),
            "code_hash": self._generate_hash(code_path),
            "model_hash": self._generate_hash(model_manifest_path),
            "update_interval_bars": self.update_interval,
            "timeframe": "12h"  # Explicit timeframe marker
        }
        
        os.makedirs(self.output_dir, exist_ok=True)
        with open(self.manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

    def track_event(self, stream_name: str, ts: float = None):
        """Increment count for a stream and record last timestamp"""
        if stream_name not in self.tracked_streams:
            return
            
        self.stream_counts[stream_name] = self.stream_counts.get(stream_name, 0) + 1
        
        if ts:
            # Convert ms timestamp to ISO
            try:
                dt = datetime.fromtimestamp(ts / 1000.0)
                self.stream_last_ts[stream_name] = dt.isoformat()
            except Exception:
                pass
        else:
            self.stream_last_ts[stream_name] = datetime.now().isoformat()

    def update(self):
        """Update the manifest file on disk (overwrite)"""
        try:
            # Read existing to preserve hashes
            if os.path.exists(self.manifest_path):
                with open(self.manifest_path, 'r') as f:
                    manifest = json.load(f)
            else:
                return # Should have been initialized

            manifest["end_ts"] = datetime.now().isoformat()
            manifest["stream_counts"] = self.stream_counts
            manifest["stream_last_ts"] = self.stream_last_ts
            
            with open(self.manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
        except Exception:
            pass # Fail silently to avoid crashing the bot

    def finalize(self):
        """Final update of the manifest before shutdown"""
        self.update()
