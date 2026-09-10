from src.normalize.keyword import normalize_keyword, unique_keywords


def parse_csv(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    row: list[str] = []
    cell = ""
    in_quotes = False
    src = text.lstrip("\ufeff")
    i = 0
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ""
        if in_quotes:
            if ch == '"' and nxt == '"':
                cell += '"'
                i += 2
                continue
            if ch == '"':
                in_quotes = False
            else:
                cell += ch
            i += 1
            continue
        if ch == '"':
            in_quotes = True
            i += 1
            continue
        if ch == ",":
            row.append(cell)
            cell = ""
            i += 1
            continue
        if ch == "\r":
            i += 1
            continue
        if ch == "\n":
            row.append(cell)
            rows.append(row)
            row = []
            cell = ""
            i += 1
            continue
        cell += ch
        i += 1
    if cell or row:
        row.append(cell)
        rows.append(row)
    return [r for r in rows if any(c.strip() for c in r)]


def test_normalize_skips_others_and_short():
    assert normalize_keyword("Others") is None
    assert normalize_keyword("OTHERS") is None
    assert normalize_keyword("ri") is None
    assert normalize_keyword("  Rice  ") == "rice"


def test_unique_collapses_case():
    assert unique_keywords(["Rice", "rice", "Others", "mini mogra rice 5 kg"]) == [
        "rice",
        "mini mogra rice 5 kg",
    ]


def test_csv_quoted_store_name():
    table = parse_csv(
        'Store Name,Area,Pincode,Latitude,Longitude\n'
        '"Blinkit, Koregaon Park",Koregaon,411001,18.536208,73.893837\n'
    )
    assert table[0][0] == "Store Name"
    assert table[1][0] == "Blinkit, Koregaon Park"
    assert table[1][2] == "411001"
