FROM python:3.12.13-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv==0.10.0 \
 && uv sync --locked --no-dev --no-install-project
COPY . .
ENV PATH="/app/.venv/bin:${PATH}" PYTHONPATH="/app/src"
EXPOSE 8010
CMD ["uvicorn","production.agentops_service.app.main:app","--host","0.0.0.0","--port","8010"]
