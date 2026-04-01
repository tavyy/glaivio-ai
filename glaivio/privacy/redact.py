def redact(text: str) -> tuple[str, dict]:
    """
    Scan text for PII using DataFog, replace with numbered placeholders.
    Returns (redacted_text, mapping) where mapping is placeholder → original value.

    The mapping is passed to rehydrate() to restore real values in the LLM's reply.
    """
    try:
        from datafog import scan_prompt
        result = scan_prompt(text, engine="regex")
        entities = getattr(result, "entities", [])

        if not entities:
            print("[Glaivio] ✓ Privacy: no PII detected")
            return text, {}

        mapping = {}
        redacted = text
        counters = {}

        # Skip entity types that skills need for booking (names, phones)
        SKIP_TYPES = {"PERSON", "PHONE", "PHONE_NUMBER"}

        # Sort by length descending to avoid partial replacements
        sorted_entities = sorted(entities, key=lambda e: len(str(e.value)), reverse=True)

        for entity in sorted_entities:
            value = str(entity.value)
            etype = str(entity.type).upper()

            if not value or value not in redacted:
                continue

            if etype in SKIP_TYPES:
                print(f"[Glaivio] ✓ Privacy: kept '{value}' ({etype}) for skill use")
                continue

            counters[etype] = counters.get(etype, 0) + 1
            placeholder = f"[{etype}_{counters[etype]}]"
            mapping[placeholder] = value
            redacted = redacted.replace(value, placeholder)
            print(f"[Glaivio] 🔒 Redacted: '{value}' → '{placeholder}'")

        print(f"[Glaivio] 🔒 Sending to LLM: {redacted}")
        return redacted, mapping

    except ImportError:
        raise ImportError(
            "Privacy redaction requires datafog.\n"
            "Install it with: pip install glaivio-ai[privacy]"
        )


def rehydrate(text: str, mapping: dict) -> str:
    """
    Replace placeholders in the LLM reply with the original PII values.
    Restores personalisation after the LLM has processed the redacted message.
    """
    print(f"[Glaivio] 🔓 Re-hydrating reply with {len(mapping)} value(s)")
    for placeholder, original in mapping.items():
        if placeholder in text:
            print(f"[Glaivio] 🔓 Restored: '{placeholder}' → '{original}'")
            text = text.replace(placeholder, original)
    return text
