"""
Prometheus metrics helpers with safe fallbacks when prometheus_client is unavailable.
"""

from typing import Any

try:
    from prometheus_client import Counter, Histogram, CONTENT_TYPE_LATEST, generate_latest
    PROMETHEUS_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    PROMETHEUS_AVAILABLE = False

    class _NoopMetric:
        def labels(self, *args: Any, **kwargs: Any) -> "_NoopMetric":
            return self

        def inc(self, amount: float = 1.0) -> None:
            return None

        def observe(self, amount: float) -> None:
            return None

    def Counter(name: str, documentation: str, labelnames: list[str] | None = None):  # type: ignore
        return _NoopMetric()

    def Histogram(name: str, documentation: str, buckets: tuple[float, ...] | None = None, labelnames: list[str] | None = None):  # type: ignore
        return _NoopMetric()

    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    def generate_latest() -> bytes:  # type: ignore
        return b""


# Email scanning metrics
FILES_PROCESSED = Counter(
    "files_processed_total",
    "Total number of files processed from email scans",
)

EMAILS_INVOICES_FOUND = Counter(
    "emails_invoices_found_total",
    "Total number of invoices discovered via email scanning",
)

EMAIL_DUPLICATES = Counter(
    "email_duplicates_total",
    "Total number of duplicates encountered during email pipeline",
    ["type"],  # attachment, create_invoice, file_store_skip
)

# OCR metrics
OCR_REQUESTS_TOTAL = Counter(
    "ocr_requests_total",
    "Total number of OCR requests, labeled by result",
    ["result"],  # reused_invoice, cache_hit, success, failed, error
)

OCR_DURATION_SECONDS = Histogram(
    "ocr_duration_seconds",
    "Duration of OCR operations in seconds",
    labelnames=["result"],
)


