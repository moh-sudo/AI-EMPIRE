"""Partner Verification Agent v0.2 -- Fixera Division.

Flags missing or stale onboarding requirements per partner, for
Mohamed's review. NEVER approves, rejects, or changes
verification_status itself -- that decision belongs to Mohamed alone,
per explicit design (see shared/prompts/fixera_partner-verification_v2.json).

Reads real data via shared.fixera_connector's
ai_empire_partner_verification_summary view. That view runs every
string leaf of Fixera's workers.service_details through
ai_empire_redact_to_presence(), so this agent only ever sees whether a
required field/document is present (and, for *ExpiryDate/*Date fields,
whether it's current) -- never the underlying national ID number,
photo URL, phone number, or name. See
infrastructure/fixera_connector_reference.sql.

Requirements below are drawn directly from Fixera's real Partner
Onboarding & Qualification Checklist and the 6 Partner-Specific
Agreements (FIXERA-LEGAL-DOCUMENTATION-CORRECTED.txt, Sections 3 & 5),
cross-referenced against what worker/src/pages/auth/OnboardingPage.jsx
actually captures into service_details.
"""

from dataclasses import dataclass, field
from typing import Any


def _get(d: Any, path: str) -> Any:
    """Walks a dotted path through nested dicts. Returns None if any
    segment is missing -- treated the same as "not present"."""
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _present(record: dict[str, Any], path: str) -> bool:
    return bool(_get(record, path))


def _min_count(record: dict[str, Any], path: str, min_items: int, required_key: str | None = None) -> bool:
    """For array fields (crew, references, multi-select chips). If
    required_key is given, counts only elements where that nested key
    is truthy (e.g. references with both name and phone filled)."""
    arr = _get(record, path)
    if not isinstance(arr, list):
        return False
    if required_key is None:
        return len(arr) >= min_items
    complete = [item for item in arr if isinstance(item, dict) and item.get(required_key)]
    return len(complete) >= min_items


# Core presence flags live at the top level of the view row, not nested
# under service_details_presence.
CORE_REQUIREMENTS: list[tuple[str, str]] = [
    ("has_profile_photo", "Profile photo"),
    ("has_id_photo", "National ID / passport photo"),
]

BASE_SD_REQUIREMENTS: list[tuple[str, str]] = [
    ("emergencyContact.name", "Emergency contact name"),
    ("emergencyContact.phone", "Emergency contact phone"),
    ("termsAccepted", "Terms & conditions accepted"),
]

POLICY_REQUIREMENTS: list[tuple[str, str]] = [
    ("policies.partnerAgreement", "Partner Agreement accepted"),
    ("policies.codeOfConduct", "Code of Conduct accepted"),
    ("policies.damageLiability", "Damage & Liability Policy accepted"),
    ("policies.customerPropertyProtection", "Customer Property Protection Policy accepted"),
    ("policies.cancellation", "Cancellation Policy accepted"),
]

# Worker sub-services (role == "worker", branches on service_details.service)
WORKER_SERVICE_REQUIREMENTS: dict[str, list[tuple[str, str]]] = {
    "Plumbing": [
        ("plumbing.certUrl", "Plumbing certificate/license"),
        ("plumbing.portfolioUrl", "Portfolio photo"),
        ("plumbing.backgroundCheckUrl", "Background check certificate"),
        ("plumbing.backgroundCheckDate", "Background check current (< 6 months)"),
        ("plumbing.criminalDecl", "Criminal record declaration"),
    ],
    "Electrical": [
        ("electrical.erbCertUrl", "ERB registration certificate"),
        ("electrical.insuranceUrl", "Public liability insurance certificate"),
        ("electrical.epraCompliant", "EPRA compliance confirmed"),
        ("electrical.backgroundCheckUrl", "Background check certificate"),
        ("electrical.backgroundCheckDate", "Background check current (< 6 months)"),
        ("electrical.criminalDecl", "Criminal record declaration"),
    ],
    "Painting": [
        ("painting.portfolioUrl", "Portfolio photo"),
        ("painting.backgroundCheckUrl", "Background check certificate"),
        ("painting.backgroundCheckDate", "Background check current (< 6 months)"),
        ("painting.criminalDecl", "Criminal record declaration"),
    ],
    "Cleaning": [
        ("cleaning.bgCheckUrl", "Background check certificate"),
        ("cleaning.bgCheckDate", "Background check current (< 6 months)"),
        ("cleaning.criminalDecl", "Criminal record declaration"),
    ],
}

RIDER_REQUIREMENTS: list[tuple[str, str]] = [
    ("dob", "Date of birth (18+ proof)"),
    ("proofOfResidenceUrl", "Proof of residence"),
    ("backgroundCheckUrl", "Background check certificate"),
    ("backgroundCheckDate", "Background check current (< 6 months)"),
    ("license.url", "Driving license photo"),
    ("vehicle.plate", "Vehicle number plate"),
    ("vehicle.regUrl", "Vehicle logbook"),
    ("vehicle.insuranceUrl", "Vehicle insurance certificate"),
    ("gpsConsent", "GPS tracking consent"),
]

VENDOR_REQUIREMENTS: list[tuple[str, str]] = [
    ("business.regUrl", "Business registration certificate"),
    ("business.docs.kraPinCertUrl", "KRA PIN certificate"),
    ("business.docs.taxComplianceCertUrl", "Tax compliance certificate"),
    ("business.docs.licenseUrl", "Business operating license"),
    ("business.docs.addressProofUrl", "Business address proof"),
    ("insurance.certUrl", "Public liability insurance certificate (>= KSh 5M)"),
    ("insurance.expiryDate", "Insurance not expired"),
]

SUPPLIER_REQUIREMENTS: list[tuple[str, str]] = [
    ("business.regUrl", "Certificate of Incorporation"),
    ("business.docs.kraPinCertUrl", "KRA PIN certificate"),
    ("business.docs.taxComplianceCertUrl", "Tax compliance certificate"),
    ("business.docs.licenseUrl", "Trading license"),
    ("business.docs.addressProofUrl", "Business address proof"),
    ("insurance.certUrl", "Product liability insurance certificate"),
    ("insurance.expiryDate", "Insurance not expired"),
    ("supplyChainDocUrl", "Supply chain documentation"),
]

MOVER_REQUIREMENTS: list[tuple[str, str]] = [
    ("business.regUrl", "Business/company registration certificate"),
    ("businessLicenseUrl", "Business operating license"),
    ("fleet.plateNumber", "Fleet vehicle plate number"),
    ("fleet.insuranceUrl", "Fleet insurance certificate"),
    ("fleet.logbookUrl", "Fleet logbook"),
    ("fleet.safetyEquipmentDecl", "Crew safety equipment declaration"),
    ("insurance.certUrl", "Liability insurance certificate (>= KSh 10M)"),
    ("insurance.expiryDate", "Insurance not expired"),
]

WATER_CARRIER_REQUIREMENTS: list[tuple[str, str]] = [
    ("business.regUrl", "Business/company registration certificate (if applicable)"),
    ("waterQuality.certUrl", "Water quality test certificate"),
    ("waterQuality.sourceDocUrl", "Water source documentation"),
    ("waterQuality.hygieneDecl", "Hygiene declaration"),
    ("healthCertUrl", "Health/fitness certification"),
    ("backgroundCheckUrl", "Background check clearance"),
]


@dataclass
class VerificationFlag:
    partner_id: str
    partner_role: str
    missing: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not self.missing


def check_partner(record: dict[str, Any]) -> VerificationFlag:
    """Evaluates one partner_verification view row against its role's
    real requirements. Returns every missing/stale item -- never a
    verdict, never an approve/reject action."""
    role = record.get("partner_role") or "worker"
    sd = record.get("service_details_presence") or {}
    missing: list[str] = []

    for key, label in CORE_REQUIREMENTS:
        if not record.get(key):
            missing.append(label)

    for path, label in BASE_SD_REQUIREMENTS:
        if not _present(sd, path):
            missing.append(label)

    if role in ("worker", "rider", "mover", "water_carrier", "vendor", "supplier"):
        for path, label in POLICY_REQUIREMENTS:
            if not _present(sd, path):
                missing.append(label)

    if role == "worker":
        service = sd.get("service")
        service_reqs = WORKER_SERVICE_REQUIREMENTS.get(service, [])
        if not service_reqs:
            missing.append(f"Unrecognized/unset service type ({service!r}) -- cannot verify requirements")
        for path, label in service_reqs:
            if not _present(sd, path):
                missing.append(label)

    elif role == "rider":
        for path, label in RIDER_REQUIREMENTS:
            if not _present(sd, path):
                missing.append(label)

    elif role == "vendor":
        for path, label in VENDOR_REQUIREMENTS:
            if not _present(sd, path):
                missing.append(label)
        if not _min_count(sd, "references", 3, required_key="name"):
            missing.append("Professional references (3 minimum)")

    elif role == "supplier":
        for path, label in SUPPLIER_REQUIREMENTS:
            if not _present(sd, path):
                missing.append(label)
        if not _min_count(sd, "references", 3, required_key="name"):
            missing.append("Professional references (3 minimum)")

    elif role == "mover":
        for path, label in MOVER_REQUIREMENTS:
            if not _present(sd, path):
                missing.append(label)
        if not _min_count(sd, "crew", 1, required_key="idPhotoUrl"):
            missing.append("At least one crew member with ID photo")
        if not _min_count(sd, "references", 2, required_key="name"):
            missing.append("Professional references (2 minimum)")

    elif role == "water_carrier":
        for path, label in WATER_CARRIER_REQUIREMENTS:
            if not _present(sd, path):
                missing.append(label)
        if not _min_count(sd, "crew", 1, required_key="idPhotoUrl"):
            missing.append("At least one staff member with ID photo")

    return VerificationFlag(partner_id=record["id"], partner_role=role, missing=missing)


def _is_self_referential_test_data(partner_id: str, bookings: list[dict[str, Any]]) -> bool:
    """True if this partner has any booking where customer_id equals
    worker_id (the same account booking a service from itself) -- a
    real customer/worker pair can never produce that, so it's a
    reliable signature of dev/test data rather than a genuine
    unverified partner.

    Found via a real live investigation (2026-07-31): the one partner
    this agent had been flagging turned out to be Mohamed's own
    dev-testing account (full_name "Mohamed", 0 real jobs, a single
    self-booked test booking dated 2026-05-30), not an actual
    compliance gap. Excluded here -- a read-side filter only -- per
    Mohamed's explicit instruction not to touch production data; the
    underlying record's verification_status is left exactly as-is."""
    return any(b.get("customer_id") == partner_id and b.get("worker_id") == partner_id for b in bookings)


def run_verification_sweep() -> list[VerificationFlag]:
    """Live entry point: fetches every completed-onboarding partner via
    the Fixera connector and returns only the ones with something
    missing or stale, for Mohamed's review. Clean partners are omitted,
    not auto-approved -- this agent never changes verification_status.
    Partners whose only linked booking is self-referential (see
    _is_self_referential_test_data) are also excluded -- known dev/test
    artifacts, not real compliance gaps."""
    from shared.fixera_connector import fetch_all

    partners = fetch_all("partner_verification")
    bookings = fetch_all("bookings")
    flags = [check_partner(p) for p in partners]
    return [f for f in flags if not f.is_clean and not _is_self_referential_test_data(f.partner_id, bookings)]
