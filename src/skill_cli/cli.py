from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from skill_cli import style
from skill_cli.banner import print_banner
from skill_cli.github_install import install_recommendations
from skill_cli.project_context import build_project_context
from skill_cli.recommender import DEFAULT_MODEL, SkillRecommender


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skill-cli",
        description="Ask for project skills in plain English, review recommendations, and install them locally.",
    )
    parser.add_argument(
        "request",
        nargs="*",
        help="Project description in plain English. If omitted, skill-cli will prompt for it.",
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Workspace to inspect and install skills into (default: current directory).",
    )
    parser.add_argument(
        "--skills-dir",
        default="skills",
        help="Folder to create inside the project for downloaded skills (default: skills).",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("SKILL_CLI_MODEL", DEFAULT_MODEL),
        help=f"Model deployment name on Foundry (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Maximum number of skill recommendations to show (default: 5).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the approval prompt and install all recommended skills.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    print_banner(args.model)
    validate_foundry_env(parser)

    project_dir = Path(args.project_dir).resolve()
    if not project_dir.exists():
        parser.error(f"Project directory does not exist: {project_dir}")

    user_request = " ".join(args.request).strip() if args.request else prompt_for_request()
    if not user_request:
        parser.error("A project description is required.")

    style.status(f"Scanning project context in {project_dir}")
    project_context = build_project_context(project_dir)

    style.status(f"Asking {args.model} on Foundry to search skills.sh")
    recommender = SkillRecommender(model=args.model)
    try:
        recommendations = recommender.recommend(
            user_request=user_request,
            project_context=project_context,
            top_k=max(1, min(args.top_k, 5)),
        )
    except Exception as exc:
        style.error(f"Failed to get recommendations: {exc}")
        return 1

    if not recommendations:
        style.error("No matching skills were found.")
        return 1

    style.section(f"Recommended skills ({len(recommendations)})")
    for index, recommendation in enumerate(recommendations, start=1):
        style.card(
            index=index,
            slug=recommendation.skill_slug,
            repo=f"{recommendation.owner}/{recommendation.repo}",
            reason=recommendation.reason,
            url=recommendation.skill_url,
        )

    if not args.yes and not style.confirm(f"Install these into ./{args.skills_dir} ?"):
        print()
        style.skipped("No files were written.")
        return 0

    print()
    style.status(f"Installing skills into {project_dir / args.skills_dir}")
    try:
        results = install_recommendations(
            recommendations=recommendations,
            project_dir=project_dir,
            skills_dir_name=args.skills_dir,
        )
    except Exception as exc:
        style.error(f"Installation failed: {exc}")
        return 1

    style.section("Install summary")
    for result in results:
        slug = result.recommendation.skill_slug
        if result.skipped:
            style.skipped(f"{slug}  already installed")
        else:
            style.success(f"{slug}  {result.file_count} files  →  {result.destination}")
    print()
    style.status(f"Manifest: {project_dir / args.skills_dir / 'manifest.json'}")
    return 0


def prompt_for_request() -> str:
    return style.ask("What are you building?")


def validate_foundry_env(parser: argparse.ArgumentParser) -> None:
    missing = [name for name in ("FOUNDRY_API_KEY", "FOUNDRY_ENDPOINT") if not os.getenv(name)]
    if missing:
        parser.error(f"Environment variable(s) not set: {', '.join(missing)}")
