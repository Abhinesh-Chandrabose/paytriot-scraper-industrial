# Maintainer's Guide - GOscraper Industrial

This guide outlines the architecture and standards for the GOscraper project.

## 🏗 Architecture
The project follows a **Modular Monorepo** structure:
- `apps/api`: FastAPI backend with dependency injection for skills.
- `apps/web-app`: Vite + React + TypeScript frontend.
- `skills/`: Encapsulated business logic (Scraping, AI).
- `.agents/skills`: Private agent rules and personas.

## 🛠 Adding a New Skill
1.  Create a subdirectory in `skills/`.
2.  Add a `SKILL.md` documenting the purpose and risks.
3.  Implement the logic in a Python class.
4.  Expose the skill via `apps/api/main.py`.

## 🛡 Security Standards
- **Prompt Injection Guard**: All user-provided or scraped text must pass through `SecurityGuard.sanitize_scraped_text()` before being sent to an LLM.
- **Environment Isolation**: Never hardcode API keys. Use `.env` and `os.getenv()`.

## 🚀 Deployment
- **Backend**: Use the included `Dockerfile` (to be optimized).
- **Frontend**: Build with `npm run build` and host as static assets or via a CDN.
- **Database**: MongoDB (Local or Atlas).

## 🧪 Validation
Run the internal validation suite:
```bash
python3 tools/validate.py
```
