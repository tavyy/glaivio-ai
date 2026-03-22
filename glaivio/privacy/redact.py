import re


# Patterns to redact before sending to LLM
_PATTERNS = [
    (re.compile(r"\b\+?[\d\s\-().]{10,15}\b"), "[PHONE]"),          # phone numbers
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL]"),  # emails
    (re.compile(r"\b[A-Z]{1,2}\d{6}[A-Z]?\b"), "[NHS_NUMBER]"),     # NHS numbers
    (re.compile(r"\b\d{2}/\d{2}/\d{4}\b"), "[DOB]"),                # dates of birth
    (re.compile(r"\b[A-Z]{2}\d{6}[A-Z]\b"), "[NI_NUMBER]"),         # NI numbers
]


def redact(text: str) -> str:
    """
    Redact PII from text before sending to an LLM.
    Replaces phone numbers, emails, NHS numbers, dates of birth, NI numbers.
    """
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text
