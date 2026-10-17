# Rakathon2026 — MDT Copilot

AI-assisted preparation and recording of multidisciplinary oncology tumour boards (MDT).
AI prepares and cites; clinicians decide.

- Brief: [docs/brief.md](docs/brief.md) (original: [docs/brief.docx](docs/brief.docx)); other
  domain docs are listed in [AGENTS.md](AGENTS.md)
- How to run, rules, workflow: [AGENTS.md](AGENTS.md)
- Architecture: [docs/architecture.md](docs/architecture.md) · Decisions: [docs/decisions.md](docs/decisions.md) · Status: [docs/status.md](docs/status.md)
- IRIS FHIR operation, Docker configuration, and deployment with the web app:
  [docs/iris-fhir-deployment.md](docs/iris-fhir-deployment.md)

Quick start (put the organisers' dataset in `Dataset/` first; it's git-ignored):

```sh
cp .env.example .env
docker compose up -d fhir
(cd backend && uv sync && uv run mdt-backend) &
(cd frontend && npm install && npm run dev)
```
