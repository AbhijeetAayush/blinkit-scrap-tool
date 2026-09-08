SYNONYMS: dict[str, str] = {}


def normalize_brand(name: str | None) -> str:
    if not name:
        return ""
    key = " ".join(name.lower().split())
    return SYNONYMS.get(key, key)
