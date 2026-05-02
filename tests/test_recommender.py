import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_cli.recommender import (
    DEFAULT_MODEL,
    _build_recommendations,
    _extract_tool_input,
    _format_candidates,
)


class RecommenderTests(unittest.TestCase):
    def test_default_model_is_anthropic(self) -> None:
        self.assertIn("claude", DEFAULT_MODEL)

    def test_format_candidates_includes_slug_and_title(self) -> None:
        candidates = [
            {
                "owner": "anthropics",
                "repo": "skills",
                "skill_slug": "frontend-design",
                "title": "Frontend Design",
                "description": "Helps build beautiful UIs.",
            }
        ]
        text = _format_candidates(candidates)
        self.assertIn("frontend-design", text)
        self.assertIn("Frontend Design", text)
        self.assertIn("anthropics/skills", text)

    def test_extract_tool_input_returns_none_when_no_tool_use(self) -> None:
        block = MagicMock()
        block.type = "text"
        response = MagicMock()
        response.content = [block]
        self.assertIsNone(_extract_tool_input(response))

    def test_extract_tool_input_returns_input_from_tool_block(self) -> None:
        block = MagicMock()
        block.type = "tool_use"
        block.name = "rank_skills"
        block.input = {"recommendations": []}
        response = MagicMock()
        response.content = [block]
        self.assertEqual(_extract_tool_input(response), {"recommendations": []})

    def test_build_recommendations_maps_to_candidates(self) -> None:
        candidates = [
            {
                "owner": "anthropics",
                "repo": "skills",
                "skill_slug": "frontend-design",
                "title": "Frontend Design",
                "description": "Helps build beautiful UIs.",
                "skill_url": "https://skills.sh/anthropics/skills/frontend-design",
            }
        ]
        tool_input = {
            "recommendations": [
                {
                    "owner": "anthropics",
                    "repo": "skills",
                    "skill_slug": "frontend-design",
                    "reason": "Matches React UI work.",
                }
            ]
        }
        results = _build_recommendations(tool_input, candidates)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].owner, "anthropics")
        self.assertEqual(results[0].skill_slug, "frontend-design")
        self.assertEqual(results[0].reason, "Matches React UI work.")

    def test_build_recommendations_ignores_hallucinated_skills(self) -> None:
        candidates = [
            {
                "owner": "anthropics",
                "repo": "skills",
                "skill_slug": "frontend-design",
                "title": "Frontend Design",
                "description": "",
                "skill_url": "https://skills.sh/anthropics/skills/frontend-design",
            }
        ]
        tool_input = {
            "recommendations": [
                {
                    "owner": "fake-owner",
                    "repo": "fake-repo",
                    "skill_slug": "does-not-exist",
                    "reason": "Hallucinated by LLM.",
                }
            ]
        }
        results = _build_recommendations(tool_input, candidates)
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
