import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_cli.catalog import _score, _tokenize, load_catalog, search_catalog


class CatalogTests(unittest.TestCase):
    def test_catalog_loads_and_has_skills(self) -> None:
        catalog = load_catalog()
        self.assertGreater(len(catalog), 0)
        first = catalog[0]
        self.assertIn("owner", first)
        self.assertIn("repo", first)
        self.assertIn("skill_slug", first)

    def test_tokenize_removes_stop_words(self) -> None:
        tokens = _tokenize("I am building a React app for the web")
        self.assertIn("react", tokens)
        self.assertIn("app", tokens)
        self.assertNotIn("i", tokens)
        self.assertNotIn("a", tokens)
        self.assertNotIn("the", tokens)

    def test_score_boosts_slug_matches(self) -> None:
        skill = {
            "skill_slug": "frontend-design",
            "title": "Frontend Design",
            "description": "Helps build UIs.",
            "owner": "anthropics",
            "repo": "skills",
            "_lc_slug": "frontend-design",
            "_lc_title": "frontend design",
            "_lc_description": "helps build uis.",
            "_lc_owner": "anthropics",
            "_lc_repo": "skills",
        }
        tokens_slug = _tokenize("frontend design components")
        tokens_desc = _tokenize("helps ui tools")
        self.assertGreater(_score(skill, tokens_slug), _score(skill, tokens_desc))

    def test_search_returns_relevant_results(self) -> None:
        results = search_catalog("React frontend design", n=5)
        self.assertGreater(len(results), 0)
        slugs = [r["skill_slug"] for r in results]
        # frontend-design is the most obvious match
        self.assertIn("frontend-design", slugs)

    def test_search_pads_with_catalog_entries_when_few_matches(self) -> None:
        results = search_catalog("xyzzy nonexistent gobbledygook", n=10)
        # Should still return entries (padded from catalog top)
        self.assertGreater(len(results), 0)

    def test_search_result_slugs_are_unique(self) -> None:
        results = search_catalog("design frontend react typescript", n=15)
        slugs = [r["skill_slug"] for r in results]
        self.assertEqual(len(slugs), len(set(slugs)))


if __name__ == "__main__":
    unittest.main()
