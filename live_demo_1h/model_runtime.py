"""Thin wrapper exposing the shared ModelRuntime implementation."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live_demo.model_runtime import ModelRuntime

__all__ = ["ModelRuntime"]
