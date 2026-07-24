from __future__ import annotations

import re
from dataclasses import dataclass

from menu_data import ALIASES, MENU_CATALOG, SEMANTIC_GROUPS, Menu


@dataclass(frozen=True)
class MenuProfile:
    name: str
    cuisine: str = ""
    kind: str = ""
    tags: frozenset[str] = frozenset()


def clean_text(value: str) -> str:
    return "".join(value.strip().lower().split())


def split_meals(value: str) -> list[str]:
    """한 날짜에 입력한 여러 끼니를 쉼표·슬래시·줄바꿈 등으로 분리한다."""
    parts = re.split(r"[,，、/|·&+\n;]+", value)
    meals: list[str] = []
    seen: set[str] = set()
    for part in parts:
        meal = " ".join(part.strip().split())
        normalized = clean_text(meal)
        if meal and normalized not in seen:
            meals.append(meal)
            seen.add(normalized)
    return meals


def profiles_of(value: str) -> list[MenuProfile]:
    return [profile_of(meal) for meal in split_meals(value)]


def profile_of(value: str | Menu) -> MenuProfile:
    if isinstance(value, dict):
        return MenuProfile(
            name=value["name"],
            cuisine=value["cuisine"],
            kind=value["kind"],
            tags=frozenset(value["tags"]),
        )

    cleaned = clean_text(value)
    if not cleaned:
        return MenuProfile(name="")
    cleaned = clean_text(ALIASES.get(cleaned, cleaned))

    for menu in MENU_CATALOG:
        menu_clean = clean_text(menu["name"])
        if cleaned == menu_clean or (len(cleaned) >= 2 and cleaned in menu_clean):
            return profile_of(menu)

    keyword_kinds = {
        "찌개": ("한식", "찌개", {"밥", "국물"}),
        "국밥": ("한식", "국밥", {"밥", "국물"}),
        "탕": ("한식", "탕", {"밥", "국물"}),
        "국수": ("", "면", {"면"}),
        "면": ("", "면", {"면"}),
        "덮밥": ("", "덮밥", {"밥"}),
        "샐러드": ("양식", "샐러드", {"채소", "가벼움"}),
    }
    for keyword, (cuisine, kind, tags) in keyword_kinds.items():
        if keyword in cleaned:
            return MenuProfile(value.strip(), cuisine, kind, frozenset(tags))
    return MenuProfile(name=value.strip())


def local_similarity(left: MenuProfile, right: MenuProfile) -> float:
    if not left.name or not right.name:
        return 0.0
    left_name, right_name = clean_text(left.name), clean_text(right.name)
    if left_name == right_name:
        return 1.0

    for group in SEMANTIC_GROUPS:
        normalized = {clean_text(name) for name in group}
        if left_name in normalized and right_name in normalized:
            return 0.84

    score = 0.0
    if left.kind and left.kind == right.kind:
        score += 0.44
    if left.cuisine and left.cuisine == right.cuisine:
        score += 0.20
    union = left.tags | right.tags
    if union:
        score += 0.30 * len(left.tags & right.tags) / len(union)
    return round(min(score, 1.0), 3)
