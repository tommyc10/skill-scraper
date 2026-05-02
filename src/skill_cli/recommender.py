from __future__ import annotations

import os
from typing import Any

import anthropic

from skill_cli.catalog import search_catalog
from skill_cli.models import SkillRecommendation

DEFAULT_MODEL = "claude-haiku-4-5-20251001"

_RANK_TOOL: dict[str, Any] = {
    "name": "rank_skills",
    "description": (
        "Select and rank the most relevant skills from the provided candidates "
        "for the user's project. Only include skills that genuinely fit."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "skill_slug": {"type": "string"},
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "reason": {
                            "type": "string",
                            "description": "One sentence explaining why this skill fits the project.",
                        },
                    },
                    "required": ["skill_slug", "owner", "repo", "reason"],
                },
            }
        },
        "required": ["recommendations"],
    },
}

_SYSTEM_PROMPT = """\
You are a skill recommendation assistant for skills.sh, a marketplace of reusable AI agent prompt modules.

Given a list of candidate skills (with slugs, titles, and descriptions) and a user's project description, \
select the skills that genuinely help with what the user is building. Rank them best-first.

Only recommend skills that are clearly relevant. It is better to return fewer high-quality matches \
than to pad the list with weak ones. Return at most the number requested.\
"""


class SkillRecommender:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or DEFAULT_MODEL
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")
        self._client = anthropic.Anthropic(api_key=api_key)

    def recommend(
        self,
        user_request: str,
        project_context: str,
        top_k: int = 5,
    ) -> list[SkillRecommendation]:
        candidates = search_catalog(user_request + " " + project_context, n=25)
        if not candidates:
            return []

        candidate_text = _format_candidates(candidates)
        user_message = (
            f"User project description:\n{user_request}\n\n"
            f"Project context:\n{project_context}\n\n"
            f"Return at most {top_k} recommendations.\n\n"
            f"Available skills:\n{candidate_text}"
        )

        response = self._client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            tools=[_RANK_TOOL],
            tool_choice={"type": "tool", "name": "rank_skills"},
            messages=[{"role": "user", "content": user_message}],
        )

        tool_input = _extract_tool_input(response)
        if tool_input is None:
            return []

        return _build_recommendations(tool_input, candidates)


def _format_candidates(candidates: list[dict]) -> str:
    lines: list[str] = []
    for i, skill in enumerate(candidates, 1):
        slug = skill["skill_slug"]
        title = skill.get("title", slug)
        description = skill.get("description", "").strip()
        owner = skill["owner"]
        repo = skill["repo"]
        line = f"{i}. [{slug}] ({owner}/{repo}) — {title}"
        if description:
            line += f"\n   {description[:200]}"
        lines.append(line)
    return "\n".join(lines)


def _extract_tool_input(response: Any) -> dict | None:
    for block in response.content:
        if block.type == "tool_use" and block.name == "rank_skills":
            return block.input
    return None


def _build_recommendations(
    tool_input: dict,
    candidates: list[dict],
) -> list[SkillRecommendation]:
    candidate_index = {
        (s["owner"], s["repo"], s["skill_slug"]): s for s in candidates
    }

    results: list[SkillRecommendation] = []
    for item in tool_input.get("recommendations", []):
        key = (item.get("owner", ""), item.get("repo", ""), item.get("skill_slug", ""))
        if not all(key):
            continue
        skill = candidate_index.get(key)
        if skill is None:
            continue
        results.append(
            SkillRecommendation(
                owner=key[0],
                repo=key[1],
                skill_slug=key[2],
                title=skill.get("title", key[2].replace("-", " ").title()),
                reason=item.get("reason", "Matches the project requirements."),
                skill_url=skill.get("skill_url", f"https://skills.sh/{key[0]}/{key[1]}/{key[2]}"),
            )
        )
    return results
