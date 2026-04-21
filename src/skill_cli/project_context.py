from __future__ import annotations

import json
import textwrap
import tomllib
from pathlib import Path


IGNORED_NAMES = {
    ".git",
    ".venv",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "skills",
}


def build_project_context(project_dir: Path) -> str:
    sections: list[str] = []
    sections.append(f"Project directory: {project_dir}")
    sections.append(summarize_top_level(project_dir))

    package_json = project_dir / "package.json"
    if package_json.exists():
        sections.append(summarize_package_json(package_json))

    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists():
        sections.append(summarize_pyproject(pyproject))

    requirements = project_dir / "requirements.txt"
    if requirements.exists():
        sections.append(summarize_requirements(requirements))

    readme = project_dir / "README.md"
    if readme.exists():
        sections.append(summarize_readme(readme))

    return "\n\n".join(section for section in sections if section)


def summarize_top_level(project_dir: Path) -> str:
    files: list[str] = []
    dirs: list[str] = []
    for entry in sorted(project_dir.iterdir(), key=lambda item: item.name.lower()):
        if entry.name in IGNORED_NAMES:
            continue
        if entry.is_dir():
            dirs.append(entry.name)
        else:
            files.append(entry.name)

    snippet: list[str] = ["Top-level layout:"]
    if dirs:
        snippet.append(f"- directories: {', '.join(dirs[:12])}")
    if files:
        snippet.append(f"- files: {', '.join(files[:12])}")
    return "\n".join(snippet)


def summarize_package_json(path: Path) -> str:
    data = json.loads(path.read_text())
    deps = sorted((data.get("dependencies") or {}).keys())
    dev_deps = sorted((data.get("devDependencies") or {}).keys())
    scripts = sorted((data.get("scripts") or {}).keys())
    lines = [
        "package.json summary:",
        f"- name: {data.get('name', 'unknown')}",
    ]
    if scripts:
        lines.append(f"- scripts: {', '.join(scripts[:10])}")
    if deps:
        lines.append(f"- dependencies: {', '.join(deps[:15])}")
    if dev_deps:
        lines.append(f"- devDependencies: {', '.join(dev_deps[:15])}")
    return "\n".join(lines)


def summarize_pyproject(path: Path) -> str:
    data = tomllib.loads(path.read_text())
    project = data.get("project") or {}
    deps = project.get("dependencies") or []
    lines = [
        "pyproject.toml summary:",
        f"- name: {project.get('name', 'unknown')}",
    ]
    if deps:
        trimmed = [str(dep) for dep in deps[:15]]
        lines.append(f"- dependencies: {', '.join(trimmed)}")
    return "\n".join(lines)


def summarize_requirements(path: Path) -> str:
    lines = [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    preview = ", ".join(lines[:15]) if lines else "none"
    return f"requirements.txt summary:\n- packages: {preview}"


def summarize_readme(path: Path) -> str:
    text = " ".join(path.read_text().split())
    excerpt = textwrap.shorten(text, width=600, placeholder="...")
    return f"README excerpt:\n{excerpt}"
