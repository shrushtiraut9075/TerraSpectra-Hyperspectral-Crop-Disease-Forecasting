import os
import time
from typing import Any, Dict

try:
    import psutil
except ImportError:
    psutil = None

import torch


class MemoryTracker:
    """Profiles system RSS and GPU memory usage."""

    def __init__(self):
        self.process = psutil.Process(os.getpid()) if psutil is not None else None
        self.start_time = 0.0
        self.start_rss = 0.0

    def start(self):
        self.start_time = time.time()
        self.start_rss = self.get_rss_mb()
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

    def get_rss_mb(self) -> float:
        if self.process is not None:
            return self.process.memory_info().rss / (1024 * 1024)
        return 0.0

    def stop(self) -> Dict[str, Any]:
        elapsed = time.time() - self.start_time
        peak_rss = self.get_rss_mb()
        peak_gpu = 0.0
        if torch.cuda.is_available():
            peak_gpu = torch.cuda.max_memory_allocated() / (1024 * 1024)

        return {
            "elapsed_seconds": round(elapsed, 4),
            "rss_mb": round(peak_rss, 2),
            "gpu_peak_mb": round(peak_gpu, 2),
        }
