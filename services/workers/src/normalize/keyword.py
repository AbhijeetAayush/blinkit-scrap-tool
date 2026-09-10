"""Keep in sync with apps/web/lib/normalize-keyword.ts."""


def normalize_keyword(raw: str) -> str | None:
    query = " ".join((raw or "").strip().split()).lower()
    if not query:
        return None
    if query == "others":
        return None
    if len(query) < 3:
        return None
    return query


def unique_keywords(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        query = normalize_keyword(raw)
        if not query or query in seen:
            continue
        seen.add(query)
        out.append(query)
    return out
