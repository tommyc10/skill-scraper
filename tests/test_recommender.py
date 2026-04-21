import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_cli.recommender import (
    DEFAULT_MODELS,
    build_text_format,
    get_openai_api_key,
    get_openai_base_url,
    normalise_provider,
    normalise_recommendations,
    parse_skill_path,
    RECOMMENDATION_SCHEMA,
)


class RecommenderTests(unittest.TestCase):
    def test_normalise_provider_accepts_aliases(self) -> None:
        self.assertEqual(normalise_provider("openai"), "openai")
        self.assertEqual(normalise_provider("grok"), "grok")
        self.assertEqual(normalise_provider("xai"), "grok")
        self.assertEqual(normalise_provider("gemini"), "gemini")
        self.assertEqual(normalise_provider("google"), "gemini")
        self.assertEqual(DEFAULT_MODELS["grok"], "grok-4.20-reasoning")
        self.assertEqual(DEFAULT_MODELS["gemini"], "gemini-3-flash-preview")

    def test_parse_skill_path_reads_canonical_skills_url(self) -> None:
        parsed = parse_skill_path(
            "https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices"
        )
        self.assertEqual(parsed, ("vercel-labs", "agent-skills", "vercel-react-best-practices"))

    def test_build_text_format_wraps_schema_for_responses_api(self) -> None:
        text_format = build_text_format(RECOMMENDATION_SCHEMA)
        self.assertEqual(text_format["type"], "json_schema")
        self.assertEqual(text_format["name"], "skill_recommendations")
        self.assertTrue(text_format["strict"])
        self.assertEqual(text_format["schema"]["type"], "object")

    def test_openai_helpers_prefer_skill_cli_specific_env_vars(self) -> None:
        env = {
            "SKILL_CLI_OPENAI_API_KEY": "skill-cli-key",
            "OPENAI_API_KEY": "openai-key",
            "SKILL_CLI_OPENAI_BASE_URL": "https://example.com/v1",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
        }
        with patch.dict("os.environ", env, clear=True):
            self.assertEqual(get_openai_api_key(), "skill-cli-key")
            self.assertEqual(get_openai_base_url(), "https://example.com/v1")

    def test_normalise_recommendations_backfills_from_url(self) -> None:
        payload = {
            "recommendations": [
                {
                    "owner": "",
                    "repo": "",
                    "skill_slug": "",
                    "title": "React Best Practices",
                    "reason": "Matches React frontend work.",
                    "skill_url": "https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices",
                }
            ]
        }

        recommendations = normalise_recommendations(payload)

        self.assertEqual(len(recommendations), 1)
        recommendation = recommendations[0]
        self.assertEqual(recommendation.owner, "vercel-labs")
        self.assertEqual(recommendation.repo, "agent-skills")
        self.assertEqual(recommendation.skill_slug, "vercel-react-best-practices")


if __name__ == "__main__":
    unittest.main()
