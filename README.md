# skill-cli

`skill-cli` is an interactive command line tool for finding and installing project skills from the Vercel skill library.

The flow is intentionally simple:

1. Launch the CLI inside your project.
2. Describe the project in plain English.
3. GPT-5.4, Grok, or Gemini reads the bundled [SKILL.md](./src/skill_cli/skill-finder/SKILL.md).
4. The model searches `skills.sh` for the best matches.
5. The CLI shows recommended skills with short reasons.
6. You approve the install.
7. The tool creates `./skills/` in the current workspace and downloads the selected skills there.

## Install

```bash
pip install -e .
```

Required environment variables:

```bash
export OPENAI_API_KEY=your_openai_api_key
```

If you're using an OpenAI-compatible endpoint instead of the default OpenAI API:

```bash
export SKILL_CLI_OPENAI_API_KEY=your_api_key
export SKILL_CLI_OPENAI_BASE_URL=https://your-endpoint.example.com/v1
```

You can also pass them at runtime:

```bash
skill-cli --provider openai \
  --openai-api-key your_api_key \
  --openai-base-url https://your-endpoint.example.com/v1
```

If you want to use Grok instead of OpenAI:

```bash
export XAI_API_KEY=your_xai_api_key
```

If you want to use Google AI Studio / Gemini:

```bash
export GEMINI_API_KEY=your_google_ai_studio_key
```

Optional but strongly recommended for faster GitHub installs and higher rate limits:

```bash
export GITHUB_TOKEN=your_github_token
```

## Usage

Interactive mode:

```bash
skill-cli
```

One-shot mode:

```bash
skill-cli "I'm building a React frontend with Azure. Keep the code simple and follow good habits."
```

Using Grok:

```bash
skill-cli --provider grok "I'm building a React frontend with Azure. Keep the code simple and follow good habits."
```

Using Gemini:

```bash
skill-cli --provider gemini "I'm building a React frontend with Azure. Keep the code simple and follow good habits."
```

Example output:

```text
$ skill-cli
Describe your project and the kinds of skills you want.
> I'm building a React frontend with Azure. Keep the code simple and follow good habits.

Recommended skills:
1. vercel-react-best-practices (vercel-labs/agent-skills)
   Matches the React frontend requirement and focuses on maintainable patterns.
   https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices
2. azure-ai (microsoft/agentics)
   Covers Azure-specific project needs mentioned in the request.
   https://skills.sh/microsoft/agentics/azure-ai

Install these into ./skills? (y/n)
```

Useful flags:

```bash
skill-cli --top-k 3
skill-cli --skills-dir .ai/skills
skill-cli --project-dir /path/to/project
skill-cli --yes "Find skills for a Next.js app with testing and clean code"
skill-cli --provider grok
skill-cli --provider grok --model grok-4.20-reasoning
skill-cli --provider gemini
skill-cli --provider gemini --model gemini-3-flash-preview
skill-cli --provider openai --openai-base-url https://your-endpoint.example.com/v1
```

## What gets written

After approval, the CLI writes:

- `./skills/<skill-name>/...` with the downloaded skill files
- `./skills/manifest.json` with the installed skill metadata

Because the folder lives in the workspace, VS Code can see it immediately.

## Project structure

- [`src/skill_cli/cli.py`](./src/skill_cli/cli.py) runs the interactive CLI flow
- [`src/skill_cli/skill-finder/SKILL.md`](./src/skill_cli/skill-finder/SKILL.md) is the bundled instruction file given to the model
- [`src/skill_cli/recommender.py`](./src/skill_cli/recommender.py) asks the model to search the Vercel skill library
- [`src/skill_cli/github_install.py`](./src/skill_cli/github_install.py) downloads the selected skill folders from GitHub

## Legacy scraper

The original bulk scraper still exists as [`scrape_skills.py`](./scrape_skills.py) if you want to download many skills directly from leaderboard pages.
