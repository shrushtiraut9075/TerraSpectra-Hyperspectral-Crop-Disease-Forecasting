import os
import time
from typing import Any, Dict

import psutil
import torch


class MemoryTracker:
    """Profiles system RSS and GPU memory usage."""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_time = 0.0
        self.start_rss = 0.0

    def start(self):
        self.start_time = time.time()
        self.start_rss = self.get_rss_mb()
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

    def get_rss_mb(self) -> float:
        return self.process.memory_info().rss / (1024 * 1024)

    def get_cuda_peak_mb(self) -> float:
        if torch.cuda.is_available():
            return torch.cuda.max_memory_allocated() / (1024 * 1024)
        return 0.0

    def stats(self) -> Dict[str, Any]:
        elapsed = time.time() - self.start_time
        current_rss = self.get_rss_mb()
        cuda_peak = self.get_cuda_peak_mb()
        return {
            "elapsed_seconds": round(elapsed, 2),
            "rss_mb": round(current_rss, 2),
            "delta_rss_mb": round(current_rss - self.start_rss, 2),
            "cuda_peak_mb": round(cuda_peak, 2),
        }
