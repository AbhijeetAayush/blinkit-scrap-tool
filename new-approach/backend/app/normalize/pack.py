from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Pack:
    pack_ml: int | None = None
    pack_g: int | None = None
    raw: str | None = None


_ML = re.compile(r"(\d+(?:\.\d+)?)\s*(ml|millilitre|milliliter)\b", re.I)
_L = re.compile(r"(\d+(?:\.\d+)?)\s*(l|ltr|litre|liter)\b", re.I)
_G = re.compile(r"(\d+(?:\.\d+)?)\s*(g|gm|gram)\b", re.I)
_KG = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|kilo)\b", re.I)


def parse_pack(raw: str | None) -> Pack:
    if not raw:
        return Pack(raw=raw)
    text = raw.strip()
    ml_m = _ML.search(text)
    if ml_m:
        return Pack(pack_ml=int(round(float(ml_m.group(1)))), raw=text)
    l_m = _L.search(text)
    if l_m:
        return Pack(pack_ml=int(round(float(l_m.group(1)) * 1000)), raw=text)
    g_m = _G.search(text)
    if g_m:
        return Pack(pack_g=int(round(float(g_m.group(1)))), raw=text)
    kg_m = _KG.search(text)
    if kg_m:
        return Pack(pack_g=int(round(float(kg_m.group(1)) * 1000)), raw=text)
    return Pack(raw=text)
