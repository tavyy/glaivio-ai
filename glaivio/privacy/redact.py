def redact(text: str) -> tuple[str, dict]:
    """
    Scan text for PII using Microsoft Presidio, replace with numbered placeholders.
    Returns (redacted_text, mapping) where mapping is placeholder → original value.

    The mapping is passed to rehydrate() to restore real values in the LLM's reply.

    Names and phone numbers are intentionally kept so booking skills work correctly.
    Sensitive identifiers (NHS numbers, NI numbers, DOBs, emails, credit cards) are redacted.
    """
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine
    except ImportError:
        raise ImportError(
            "Privacy redaction requires presidio.\n"
            "Install it with: pip install glaivio-ai[privacy]"
        )

    # Entity types to redact — skip PERSON, PHONE and DATE_TIME so booking skills work
    REDACT_TYPES = [
        "EMAIL_ADDRESS",
        "MEDICAL_LICENSE",
        "NRP",           # National Registration Number (NI numbers etc.)
        "IBAN_CODE",
        "CREDIT_CARD",
        "CRYPTO",
        "IP_ADDRESS",
        "LOCATION",
        "US_SSN",
        "UK_NHS",
    ]

    analyzer = AnalyzerEngine()
    results = analyzer.analyze(
        text=text,
        language="en",
        entities=REDACT_TYPES,
    )

    if not results:
        print("[Glaivio] ✓ Privacy: no PII detected")
        return text, {}

    # Sort by position descending to replace without offset issues
    results = sorted(results, key=lambda r: r.start, reverse=True)

    mapping = {}
    redacted = text
    counters = {}

    for result in results:
        etype = result.entity_type
        value = text[result.start:result.end]

        if not value:
            continue

        counters[etype] = counters.get(etype, 0) + 1
        placeholder = f"[{etype}_{counters[etype]}]"
        mapping[placeholder] = value
        redacted = redacted[:result.start] + placeholder + redacted[result.end:]
        print(f"[Glaivio] 🔒 Redacted: '{value}' → '{placeholder}'")

    print(f"[Glaivio] 🔒 Sending to LLM: {redacted}")
    return redacted, mapping


def rehydrate(text: str, mapping: dict) -> str:
    """
    Replace placeholders in the LLM reply with the original PII values.
    Restores personalisation after the LLM has processed the redacted message.
    """
    if not mapping:
        return text
    print(f"[Glaivio] 🔓 Re-hydrating reply with {len(mapping)} value(s)")
    for placeholder, original in mapping.items():
        if placeholder in text:
            print(f"[Glaivio] 🔓 Restored: '{placeholder}' → '{original}'")
            text = text.replace(placeholder, original)
    return text
