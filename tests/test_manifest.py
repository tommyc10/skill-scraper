import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_cli.github_install import write_manifest
from skill_cli.models import InstallResult, SkillRecommendation


class ManifestTests(unittest.TestCase):
    def test_write_manifest_records_installed_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            skills_dir = temp_path / "skills"
            skills_dir.mkdir()

            result = InstallResult(
                recommendation=SkillRecommendation(
                    owner="vercel-labs",
                    repo="agent-skills",
                    skill_slug="vercel-react-best-practices",
                    title="React Best Practices",
                    reason="Matches React frontend work.",
                    skill_url="https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices",
                ),
                destination=skills_dir / "vercel-react-best-practices",
                file_count=4,
            )

            manifest_path = write_manifest(temp_path, "skills", [result])
            payload = json.loads(manifest_path.read_text())

            self.assertEqual(manifest_path, skills_dir / "manifest.json")
            self.assertEqual(payload["skills_dir"], "skills")
            self.assertEqual(
                payload["installed_skills"][0]["skill_slug"],
                "vercel-react-best-practices",
            )
            self.assertEqual(payload["installed_skills"][0]["file_count"], 4)


if __name__ == "__main__":
    unittest.main()
