from __future__ import annotations

import heapq
import json
import re
from importlib import resources
from pathlib import Path

_CATALOG: list[dict] | None = None

STOP_WORDS = {
    "a", "an", "the", "is", "in", "for", "to", "of", "and", "or", "with",
    "that", "this", "my", "i", "we", "build", "building", "project", "using",
    "use", "help", "need", "want", "make", "create", "get", "set", "add",
    "can", "how", "do", "it", "its", "be", "as", "by", "on", "at", "from",
    "are", "was", "were", "has", "have", "had", "will", "would", "should",
    "could", "may", "some", "any", "all", "not", "no", "so", "then", "than",
}


def load_catalog() -> list[dict]:
    global _CATALOG
    if _CATALOG is not None:
        return _CATALOG

    catalog_path = Path(__file__).parent / "data" / "skills_catalog.json"
    try:
        data = json.loads(catalog_path.read_text())
    except FileNotFoundError:
        ref = resources.files("skill_cli").joinpath("data/skills_catalog.json")
        data = json.loads(ref.read_text())

    catalog = data.get("skills", [])
    for skill in catalog:
        skill["_lc_slug"] = skill.get("skill_slug", "").lower()
        skill["_lc_title"] = skill.get("title", "").lower()
        skill["_lc_description"] = skill.get("description", "").lower()
        skill["_lc_owner"] = skill.get("owner", "").lower()
        skill["_lc_repo"] = skill.get("repo", "").lower()

    _CATALOG = catalog
    return _CATALOG


def search_catalog(query: str, n: int = 25) -> list[dict]:
    catalog = load_catalog()
    tokens = _tokenize(query)

    if not tokens:
        return catalog[:n]

    scored = [(score, skill) for skill in catalog if (score := _score(skill, tokens)) > 0]
    results = [s for _, s in heapq.nlargest(n, scored, key=lambda x: x[0])]

    if len(results) < n:
        slugs = {s["skill_slug"] for s in results}
        for skill in catalog:
            if skill["skill_slug"] not in slugs:
                results.append(skill)
                if len(results) >= n:
                    break

    return results


def _tokenize(text: str) -> set[str]:
    words = set(re.findall(r"\b[a-z]+\b", text.lower()))
    return words - STOP_WORDS


def _score(skill: dict, tokens: set[str]) -> int:
    slug = skill["_lc_slug"]
    title = skill["_lc_title"]
    description = skill["_lc_description"]
    owner = skill["_lc_owner"]
    repo = skill["_lc_repo"]

    score = 0
    for token in tokens:
        if token in slug:
            score += 3
        if token in title:
            score += 2
        if token in description:
            score += 1
        if token in owner or token in repo:
            score += 1
    return score
