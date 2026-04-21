from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote

from skill_cli.models import InstallResult, SkillRecommendation

if TYPE_CHECKING:
    import httpx


GITHUB_API = "https://api.github.com"


def get_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "skill-cli",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def install_recommendations(
    recommendations: list[SkillRecommendation],
    project_dir: Path,
    skills_dir_name: str = "skills",
    sleep_seconds: float = 0.1,
) -> list[InstallResult]:
    httpx = _load_httpx()
    target_dir = project_dir / skills_dir_name
    target_dir.mkdir(parents=True, exist_ok=True)

    results: list[InstallResult] = []
    with httpx.Client(follow_redirects=True) as client:
        for recommendation in recommendations:
            destination = resolve_install_dir(target_dir, recommendation)
            if destination.exists() and any(destination.iterdir()):
                results.append(
                    InstallResult(
                        recommendation=recommendation,
                        destination=destination,
                        file_count=0,
                        skipped=True,
                    )
                )
                continue

            folder = find_skill_folder(
                client,
                recommendation.owner,
                recommendation.repo,
                recommendation.skill_slug,
            )
            if folder is None:
                raise RuntimeError(
                    f"Could not find SKILL.md folder for {recommendation.repo_slug}/{recommendation.skill_slug}"
                )

            destination.mkdir(parents=True, exist_ok=True)
            file_count = download_folder(
                client,
                recommendation.owner,
                recommendation.repo,
                folder,
                destination,
            )
            results.append(
                InstallResult(
                    recommendation=recommendation,
                    destination=destination,
                    file_count=file_count,
                    skipped=False,
                )
            )
            time.sleep(sleep_seconds)

    write_manifest(project_dir=project_dir, skills_dir_name=skills_dir_name, results=results)
    return results


def resolve_install_dir(target_dir: Path, recommendation: SkillRecommendation) -> Path:
    primary = target_dir / recommendation.skill_slug
    if not primary.exists():
        return primary

    manifest_path = target_dir / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError:
            manifest = {}
        for item in manifest.get("installed_skills", []):
            if (
                item.get("skill_slug") == recommendation.skill_slug
                and item.get("owner") == recommendation.owner
                and item.get("repo") == recommendation.repo
            ):
                return primary

    return target_dir / f"{recommendation.skill_slug}-{recommendation.owner}"


def find_skill_folder(
    client: "httpx.Client",
    owner: str,
    repo: str,
    skill: str,
) -> str | None:
    candidates = [
        skill,
        f"skills/{skill}",
        "",
    ]
    for path in candidates:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}".rstrip("/")
        response = client.get(url, headers=get_headers(), timeout=30)
        if response.status_code != 200:
            continue

        items = response.json()
        if not isinstance(items, list):
            continue

        if any(
            item.get("type") == "file" and item.get("name", "").upper() == "SKILL.MD"
            for item in items
        ):
            return path

    for prefix in ["skills", ""]:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{prefix}".rstrip("/")
        response = client.get(url, headers=get_headers(), timeout=30)
        if response.status_code != 200:
            continue

        items = response.json()
        if not isinstance(items, list):
            continue

        for item in items:
            if item.get("type") != "dir":
                continue
            folder_name = item["name"].lower()
            if folder_name in skill.lower() or skill.lower() in folder_name:
                candidate = f"{prefix}/{item['name']}".lstrip("/")
                check = client.get(
                    f"{GITHUB_API}/repos/{owner}/{repo}/contents/{candidate}",
                    headers=get_headers(),
                    timeout=30,
                )
                if check.status_code != 200:
                    continue
                sub_items = check.json()
                if isinstance(sub_items, list) and any(
                    sub.get("type") == "file" and sub.get("name", "").upper() == "SKILL.MD"
                    for sub in sub_items
                ):
                    return candidate

    query = f"filename:SKILL.md repo:{owner}/{repo}"
    search_url = f"{GITHUB_API}/search/code?q={quote(query)}"
    response = client.get(search_url, headers=get_headers(), timeout=30)
    if response.status_code == 200:
        for item in response.json().get("items", []):
            path = item.get("path", "")
            folder = "/".join(path.split("/")[:-1])
            folder_name = folder.split("/")[-1].lower() if folder else ""
            if skill.lower() in folder.lower() or folder_name in skill.lower():
                return folder
    return None


def download_folder(
    client: "httpx.Client",
    owner: str,
    repo: str,
    path: str,
    destination: Path,
) -> int:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}".rstrip("/")
    response = client.get(url, headers=get_headers(), timeout=30)
    response.raise_for_status()
    items = response.json()
    if not isinstance(items, list):
        items = [items]

    file_count = 0
    for item in items:
        item_type = item.get("type")
        name = item["name"]
        sub_destination = destination / name
        if item_type == "dir":
            sub_destination.mkdir(parents=True, exist_ok=True)
            file_count += download_folder(client, owner, repo, item["path"], sub_destination)
        elif item_type == "file":
            download_url = item.get("download_url")
            if not download_url:
                continue
            file_response = client.get(download_url, timeout=30)
            file_response.raise_for_status()
            sub_destination.parent.mkdir(parents=True, exist_ok=True)
            sub_destination.write_bytes(file_response.content)
            file_count += 1
    return file_count


def write_manifest(
    project_dir: Path,
    skills_dir_name: str,
    results: list[InstallResult],
) -> Path:
    manifest_path = project_dir / skills_dir_name / "manifest.json"
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "skills_dir": skills_dir_name,
        "installed_skills": [result.to_manifest_dict() for result in results],
    }
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n")
    return manifest_path


def _load_httpx():
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - exercised in runtime environments
        raise RuntimeError(
            "httpx is not installed. Run `pip install -e .` first."
        ) from exc
    return httpx
