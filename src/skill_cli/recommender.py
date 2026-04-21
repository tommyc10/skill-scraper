from __future__ import annotations

import json
import os
from importlib import resources
from typing import Any
from urllib.parse import urlparse

from skill_cli.models import SkillRecommendation

DEFAULT_MODEL = "gpt-5.4"


RECOMMENDATION_SCHEMA: dict[str, Any] = {
    "name": "skill_recommendations",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "skill_slug": {"type": "string"},
                        "title": {"type": "string"},
                        "reason": {"type": "string"},
                        "skill_url": {"type": "string"},
                    },
                    "required": [
                        "owner",
                        "repo",
                        "skill_slug",
                        "title",
                        "reason",
                        "skill_url",
                    ],
                },
            }
        },
        "required": ["recommendations"],
    },
}


class SkillRecommender:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or DEFAULT_MODEL
        self.instructions = resources.files("skill_cli").joinpath("skill-finder/SKILL.md").read_text()

    def recommend(
        self,
        user_request: str,
        project_context: str,
        top_k: int = 5,
    ) -> list[SkillRecommendation]:
        client = self._build_client()
        response = client.responses.create(
            model=self.model,
            reasoning={"effort": "medium"},
            input=[
                {"role": "developer", "content": self.instructions},
                {
                    "role": "user",
                    "content": (
                        "Recommend the most relevant skills for this project request.\n\n"
                        f"User request:\n{user_request}\n\n"
                        f"Project context:\n{project_context}\n\n"
                        f"Return no more than {top_k} recommendations."
                    ),
                },
            ],
            tools=[
                {
                    "type": "web_search",
                    "filters": {"allowed_domains": ["skills.sh"]},
                }
            ],
            tool_choice="auto",
            include=["web_search_call.action.sources"],
            text={"format": RECOMMENDATION_SCHEMA},
        )
        payload = json.loads(response.output_text)
        return normalise_recommendations(payload)

    def _build_client(self):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - exercised in runtime environments
            raise RuntimeError(
                "The OpenAI SDK is not installed. Run `pip install -e .` first."
            ) from exc

        return OpenAI(
            api_key=_require_env("FOUNDRY_API_KEY"),
            base_url=_require_env("FOUNDRY_ENDPOINT"),
        )


def normalise_recommendations(payload: dict[str, Any]) -> list[SkillRecommendation]:
    recommendations: list[SkillRecommendation] = []
    for item in payload.get("recommendations", []):
        owner = item.get("owner", "").strip()
        repo = item.get("repo", "").strip()
        skill_slug = item.get("skill_slug", "").strip()
        skill_url = item.get("skill_url", "").strip()

        if not owner or not repo or not skill_slug:
            parsed = parse_skill_path(skill_url)
            if parsed is not None:
                owner, repo, skill_slug = parsed

        if not owner or not repo or not skill_slug:
            continue

        title = item.get("title", "").strip() or skill_slug.replace("-", " ")
        reason = item.get("reason", "").strip() or "Matches the request."
        recommendations.append(
            SkillRecommendation(
                owner=owner,
                repo=repo,
                skill_slug=skill_slug,
                title=title,
                reason=reason,
                skill_url=skill_url or f"https://skills.sh/{owner}/{repo}/{skill_slug}",
            )
        )
    return recommendations


def parse_skill_path(url: str) -> tuple[str, str, str] | None:
    if not url:
        return None

    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != "skills.sh":
        return None

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 3:
        return None
    return parts[0], parts[1], parts[2]


def _require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value.strip():
        raise RuntimeError(f"{name} is not set.")
    return value
