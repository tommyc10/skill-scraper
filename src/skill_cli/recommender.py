from __future__ import annotations

import json
import os
from importlib import resources
from typing import Any
from urllib.parse import urlparse

from skill_cli.models import SkillRecommendation

DEFAULT_MODELS = {
    "openai": "gpt-5.4",
    "grok": "grok-4.20-reasoning",
    "gemini": "gemini-3-flash-preview",
}


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
    def __init__(
        self,
        provider: str = "openai",
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.provider = normalise_provider(provider)
        self.model = model or DEFAULT_MODELS[self.provider]
        self.api_key = api_key
        self.base_url = base_url
        self.instructions = resources.files("skill_cli").joinpath("skill-finder/SKILL.md").read_text()

    def recommend(
        self,
        user_request: str,
        project_context: str,
        top_k: int = 5,
    ) -> list[SkillRecommendation]:
        if self.provider == "gemini":
            return self._recommend_with_gemini(
                user_request=user_request,
                project_context=project_context,
                top_k=top_k,
            )

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
            text={"format": build_text_format(RECOMMENDATION_SCHEMA)},
        )
        payload = json.loads(response.output_text)
        return normalise_recommendations(payload)

    def _recommend_with_gemini(
        self,
        user_request: str,
        project_context: str,
        top_k: int,
    ) -> list[SkillRecommendation]:
        client, types = self._build_gemini_client()
        prompt = (
            f"{self.instructions}\n\n"
            "Recommend the most relevant skills for this project request.\n\n"
            f"User request:\n{user_request}\n\n"
            f"Project context:\n{project_context}\n\n"
            f"Return no more than {top_k} recommendations."
        )
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_mime_type="application/json",
                response_json_schema=RECOMMENDATION_SCHEMA["schema"],
            ),
        )
        payload = json.loads(response.text)
        return normalise_recommendations(payload)

    def _build_client(self):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - exercised in runtime environments
            raise RuntimeError(
                "The OpenAI SDK is not installed. Run `pip install -e .` first."
            ) from exc

        if self.provider == "grok":
            return OpenAI(
                api_key=self.api_key or _require_env("XAI_API_KEY"),
                base_url="https://api.x.ai/v1",
            )

        return OpenAI(
            api_key=self.api_key or get_openai_api_key(),
            base_url=self.base_url or get_openai_base_url(),
        )

    def _build_gemini_client(self):
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - exercised in runtime environments
            raise RuntimeError(
                "The Google GenAI SDK is not installed. Run `pip install -e .` first."
            ) from exc

        api_key = os.getenv("GOOGLE_API_KEY") or _require_env("GEMINI_API_KEY")
        return genai.Client(api_key=api_key), types


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


def normalise_provider(provider: str) -> str:
    value = provider.strip().lower()
    aliases = {
        "openai": "openai",
        "gpt": "openai",
        "gpt-5.4": "openai",
        "grok": "grok",
        "xai": "grok",
        "gemini": "gemini",
        "google": "gemini",
        "google-ai-studio": "gemini",
    }
    if value not in aliases:
        raise ValueError(f"Unsupported provider: {provider}")
    return aliases[value]


def _require_env(name: str) -> str:
    try:
        import os

        value = os.environ[name]
    except KeyError as exc:
        raise RuntimeError(f"{name} is not set.") from exc
    if not value.strip():
        raise RuntimeError(f"{name} is not set.")
    return value


def get_openai_api_key() -> str:
    for name in ["SKILL_CLI_OPENAI_API_KEY", "OPENAI_API_KEY"]:
        value = os.getenv(name)
        if value and value.strip():
            return value
    raise RuntimeError("SKILL_CLI_OPENAI_API_KEY or OPENAI_API_KEY is not set.")


def get_openai_base_url() -> str | None:
    for name in ["SKILL_CLI_OPENAI_BASE_URL", "OPENAI_BASE_URL"]:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return None


def build_text_format(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": schema["name"],
        "schema": schema["schema"],
        "strict": schema.get("strict", True),
    }
