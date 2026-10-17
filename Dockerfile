# One image: builds the frontend, FastAPI serves it next to /api on :8000.
# Patient data come only from the FHIR server (FHIR_BASE_URL, IRIS). Bakes in the dataset's
# guidelines/ + studie/ (knowledge.py) and the agent's briefings data/ai_cases/ (both must exist
# locally; run `uv run mdt-agent --all` first) — keep the image in a private registry.
# Mount a volume at /app/data/records (saved MDT records), or they're lost on restart.
FROM node:24-slim AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
# DejaVu: a TrueType font with Czech glyphs for the PDF export (pdf.py)
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
RUN uv sync --frozen --no-dev
COPY Dataset/guidelines/ /app/Dataset/guidelines/
COPY Dataset/studie/ /app/Dataset/studie/
COPY data/ai_cases/ /app/data/ai_cases/
COPY --from=web /app/frontend/dist /app/frontend/dist
RUN mkdir -p /app/data/records
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "mdt_backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
