import os

_configured = False


def _ensure_configured() -> None:
    global _configured
    if not _configured:
        import resend

        api_key = os.environ.get("RESEND_API_KEY")
        if not api_key or api_key == "REPLACE_ME":
            raise RuntimeError("RESEND_API_KEY not configured")
        resend.api_key = api_key
        _configured = True


def send_email(
    *,
    to: str,
    subject: str,
    html: str,
    from_address: str = "AI_EMPIRE <audit@ai-empire.fixera.africa>",
) -> dict:
    """Generic transactional email send via Resend.

    No Fixera-specific templates here by design — those are deferred
    until the Fixera/AI_EMPIRE relationship in CONTEXT.md's Phase 4 plan
    is resolved (see CONTEXT.md Session Log, 2026-07-22).
    """
    _ensure_configured()
    import resend

    return resend.Emails.send({
        "from": from_address,
        "to": [to],
        "subject": subject,
        "html": html,
    })
