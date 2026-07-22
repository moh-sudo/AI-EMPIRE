from dataclasses import dataclass

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine

    _analyzer = AnalyzerEngine()
    _anonymizer = AnonymizerEngine()
    _PRESIDIO_AVAILABLE = True
except Exception:
    _analyzer = None
    _anonymizer = None
    _PRESIDIO_AVAILABLE = False


@dataclass
class PiiScanResult:
    pii_detected: bool
    sanitized: bool
    sanitized_text: str
    status: str  # "none" | "sanitized" | "detected_unsanitized" | "scan_failed"


def scan_and_sanitize(text: str) -> PiiScanResult:
    # Fail closed: any inability to run the scan or the anonymizer is treated
    # as "not sanitized", never as "no PII found". Callers must never route
    # unsanitized CONFIDENTIAL/RESTRICTED data to cloud on the strength of a
    # failed scan.
    if not _PRESIDIO_AVAILABLE:
        return PiiScanResult(pii_detected=True, sanitized=False, sanitized_text=text, status="scan_failed")

    try:
        results = _analyzer.analyze(text=text, language="en")
    except Exception:
        return PiiScanResult(pii_detected=True, sanitized=False, sanitized_text=text, status="scan_failed")

    if not results:
        return PiiScanResult(pii_detected=False, sanitized=True, sanitized_text=text, status="none")

    try:
        anonymized = _anonymizer.anonymize(text=text, analyzer_results=results)
        return PiiScanResult(pii_detected=True, sanitized=True, sanitized_text=anonymized.text, status="sanitized")
    except Exception:
        return PiiScanResult(pii_detected=True, sanitized=False, sanitized_text=text, status="detected_unsanitized")
