from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class SkillRecommendation:
    owner: str
    repo: str
    skill_slug: str
    title: str
    reason: str
    skill_url: str

    @property
    def repo_slug(self) -> str:
        return f"{self.owner}/{self.repo}"

    def to_manifest_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class InstallResult:
    recommendation: SkillRecommendation
    destination: Path
    file_count: int
    skipped: bool = False

    def to_manifest_dict(self) -> dict[str, object]:
        payload = self.recommendation.to_manifest_dict()
        payload.update(
            {
                "destination": str(self.destination),
                "file_count": self.file_count,
                "skipped": self.skipped,
            }
        )
        return payload
