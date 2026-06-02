from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class KPISnapshot:
    rows_processed: int = 0
    bytes_processed: int = 0
    elapsed_seconds: float = 0.0
    rows_per_second: float = 0.0
    mb_per_second: float = 0.0
    eta_seconds: float | None = None


class KPITracker:
    """Real-time performance tracker for migration operations.

    Calculates rows/s, MB/s, and ETA based on accumulated progress.
    """

    def __init__(self, total_rows: int | None = None) -> None:
        self._total_rows = total_rows
        self._rows_processed: int = 0
        self._bytes_processed: int = 0
        self._start_time: float = 0.0
        self._running: bool = False

    @property
    def total_rows(self) -> int | None:
        return self._total_rows

    @total_rows.setter
    def total_rows(self, value: int | None) -> None:
        self._total_rows = value

    def start(self) -> None:
        self._start_time = time.perf_counter()
        self._running = True

    def stop(self) -> None:
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def add_rows(self, count: int, byte_size: int = 0) -> None:
        self._rows_processed += count
        self._bytes_processed += byte_size

    @property
    def rows_processed(self) -> int:
        return self._rows_processed

    @property
    def bytes_processed(self) -> int:
        return self._bytes_processed

    def snapshot(self) -> KPISnapshot:
        elapsed = time.perf_counter() - self._start_time if self._running else 0.0
        if elapsed == 0:
            return KPISnapshot(
                rows_processed=self._rows_processed,
                bytes_processed=self._bytes_processed,
            )

        rps = self._rows_processed / elapsed
        mb = self._bytes_processed / (1024 * 1024)
        mbps = mb / elapsed

        eta: float | None = None
        if self._total_rows and self._total_rows > self._rows_processed:
            remaining = self._total_rows - self._rows_processed
            eta = remaining / rps if rps > 0 else None

        return KPISnapshot(
            rows_processed=self._rows_processed,
            bytes_processed=self._bytes_processed,
            elapsed_seconds=elapsed,
            rows_per_second=rps,
            mb_per_second=mbps,
            eta_seconds=eta,
        )

    def format_snapshot(self) -> str:
        snap = self.snapshot()
        parts = [f"{snap.rows_processed:,} rows"]
        if snap.elapsed_seconds > 0:
            parts.append(f"{snap.rows_per_second:,.0f} rows/s")
            if snap.mb_per_second > 0:
                parts.append(f"{snap.mb_per_second:.2f} MB/s")
            if snap.eta_seconds is not None:
                eta_min, eta_sec = divmod(int(snap.eta_seconds), 60)
                parts.append(f"ETA {eta_min}m{eta_sec:02d}s")
        return " | ".join(parts)
