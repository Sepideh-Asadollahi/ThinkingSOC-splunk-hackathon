"""Host OS CPU and memory metrics for the dashboard."""

from __future__ import annotations

import socket

import psutil

from models.dashboard import SystemResources

_cpu_primed = False


def collect_system_resources() -> SystemResources:
    """Snapshot current host CPU and memory usage."""
    global _cpu_primed
    if not _cpu_primed:
        psutil.cpu_percent(interval=None)
        _cpu_primed = True
    cpu_percent = psutil.cpu_percent(interval=None)
    vm = psutil.virtual_memory()
    return SystemResources(
        hostname=socket.gethostname(),
        cpu_percent=round(cpu_percent, 1),
        memory_percent=round(vm.percent, 1),
        memory_used_bytes=vm.used,
        memory_total_bytes=vm.total,
    )
