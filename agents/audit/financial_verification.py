"""Financial Verification -- Audit & Verification Division.

Real checks against Fixera's actual payment data, reached through the
same scoped, read-only connector Fixera's own 8 agents use
(shared/fixera_connector.py) -- never a direct or write connection,
consistent with the data-separation principle everywhere else in this
project. Fully deterministic (arithmetic verification), no LLM needed.
"""

TOLERANCE = 1.0  # KSh -- rounding differences below this aren't worth flagging


def _safe_float(value) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def verify_commission_math(payment: dict) -> dict:
    """Checks commission_amount == amount * commission_rate (within
    tolerance) and partner_amount == amount - commission_amount.
    Returns a finding dict only if something's actually wrong."""
    amount = _safe_float(payment.get("amount"))
    rate = _safe_float(payment.get("commission_rate"))
    commission = _safe_float(payment.get("commission_amount"))
    partner_amount = _safe_float(payment.get("partner_amount"))

    expected_commission = amount * rate
    issues = []

    if abs(commission - expected_commission) > TOLERANCE:
        issues.append(
            f"commission_amount is {commission:.2f}, expected ~{expected_commission:.2f} (amount {amount:.2f} x rate {rate:.4f})"
        )

    if partner_amount and abs(partner_amount - (amount - commission)) > TOLERANCE:
        issues.append(
            f"partner_amount is {partner_amount:.2f}, expected ~{amount - commission:.2f} (amount - commission)"
        )

    if amount < 0:
        issues.append(f"negative payment amount: {amount:.2f}")

    if not issues:
        return {"flagged": False}
    return {"flagged": True, "payment_id": payment.get("id"), "issues": issues}


def run_financial_verification() -> dict:
    """Live entry point -- pulls real Fixera payments via the scoped
    connector and checks every one's math. Never raises."""
    try:
        from shared.fixera_connector import fetch_all

        payments = fetch_all("payments")
    except Exception as e:
        return {"ok": False, "reason": str(e)}

    flagged = [f for f in (verify_commission_math(p) for p in payments) if f["flagged"]]
    return {"ok": True, "checked": len(payments), "flagged_count": len(flagged), "flagged": flagged}
