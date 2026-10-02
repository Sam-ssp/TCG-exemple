import unicodedata


def normalize(text: str) -> str:
    """Lowercase and strip accents, so 'Énergie' and 'energie' compare equal."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower().strip()
