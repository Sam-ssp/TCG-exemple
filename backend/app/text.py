import unicodedata

# NFKD leaves these alone; TCGdex mixes ’ and ' in French names, keyboards type ' and "oe".
REPLACEMENTS = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "œ": "oe", "æ": "ae"})


def normalize(text: str) -> str:
    """Lowercase, strip accents and unify apostrophes, so 'Énergie' and 'energie' compare equal."""
    decomposed = unicodedata.normalize("NFKD", text.lower().translate(REPLACEMENTS))
    return "".join(c for c in decomposed if not unicodedata.combining(c)).strip()
