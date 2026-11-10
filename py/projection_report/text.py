"""Text cleanup for the PDF's built-in fonts, which use Windows-1252."""

import unicodedata

ENCODING = "cp1252"

# Characters outside Windows-1252 with a close equivalent that is inside it.
_REPLACEMENTS = {
    "μ": "µ",  # Greek mu -> micro sign
    "−": "-",       # minus sign
    "≤": "<=",
    "≥": ">=",
    "→": "->",
    " ": " ",       # thin space
    " ": " ",       # narrow no-break space
    "​": "",        # zero-width space
}


def to_pdf_text(text: str) -> str:
    """
    Make text encodable in Windows-1252 so one unusual character (for
    example a Greek mu in a drug name) doesn't abort the whole report.

    Characters with a known equivalent are mapped. Others lose accents or
    become "?".
    """
    try:
        text.encode(ENCODING)
        return text
    except UnicodeEncodeError:
        pass

    out = []
    for ch in text:
        try:
            ch.encode(ENCODING)
            out.append(ch)
            continue
        except UnicodeEncodeError:
            pass
        if ch in _REPLACEMENTS:
            out.append(_REPLACEMENTS[ch])
            continue
        base = "".join(c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c))
        out.append(base.encode(ENCODING, "replace").decode(ENCODING))
    return "".join(out)
