import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_cli.recommender import (
    DEFAULT_MODEL,
    normalise_recommendations,
    parse_skill_path,
)


class RecommenderTests(unittest.TestCase):
    def test_default_model_is_foundry_deployment(self) -> None:
        self.assertEqual(DEFAULT_MODEL, "gpt-5.4")

    def test_parse_skill_path_reads_canonical_skills_url(self) -> None:
        parsed = parse_skill_path(
            "https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices"
        )
        self.assertEqual(parsed, ("vercel-labs", "agent-skills", "vercel-react-best-practices"))

    def test_parse_skill_path_rejects_non_skills_domain(self) -> None:
        self.assertIsNone(parse_skill_path("https://github.com/owner/repo/skill"))

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
