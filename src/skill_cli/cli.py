from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

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

    print(f"Scanning project context in {project_dir}...")
    project_context = build_project_context(project_dir)

    print(f"Asking {args.model} on Foundry to search skills.sh...")
    recommender = SkillRecommender(model=args.model)
    try:
        recommendations = recommender.recommend(
            user_request=user_request,
            project_context=project_context,
            top_k=max(1, min(args.top_k, 5)),
        )
    except Exception as exc:
        print(f"Failed to get recommendations: {exc}", file=sys.stderr)
        return 1

    if not recommendations:
        print("No matching skills were found.")
        return 1

    print()
    print("Recommended skills:")
    for index, recommendation in enumerate(recommendations, start=1):
        print(
            f"{index}. {recommendation.skill_slug} "
            f"({recommendation.owner}/{recommendation.repo})"
        )
        print(f"   {recommendation.reason}")
        print(f"   {recommendation.skill_url}")

    if not args.yes and not confirm_install(args.skills_dir):
        print("No files were written.")
        return 0

    print()
    print(f"Installing skills into {project_dir / args.skills_dir}...")
    try:
        results = install_recommendations(
            recommendations=recommendations,
            project_dir=project_dir,
            skills_dir_name=args.skills_dir,
        )
    except Exception as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        return 1

    print()
    print("Install summary:")
    for result in results:
        status = "skipped" if result.skipped else f"{result.file_count} files"
        print(f"- {result.recommendation.skill_slug}: {status} -> {result.destination}")
    print(f"Manifest: {project_dir / args.skills_dir / 'manifest.json'}")
    return 0


def prompt_for_request() -> str:
    print("Describe your project and the kinds of skills you want.")
    return input("> ").strip()


def confirm_install(skills_dir: str) -> bool:
    reply = input(f"\nInstall these into ./{skills_dir}? (y/n) ").strip().lower()
    return reply in {"y", "yes"}


def validate_foundry_env(parser: argparse.ArgumentParser) -> None:
    missing = [name for name in ("FOUNDRY_API_KEY", "FOUNDRY_ENDPOINT") if not os.getenv(name)]
    if missing:
        parser.error(f"Environment variable(s) not set: {', '.join(missing)}")
