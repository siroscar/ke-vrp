FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/workspace/src \
    MPLBACKEND=Agg

WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source is bind-mounted at runtime (see docker-compose.yml / devcontainer.json),
# so edits in VS Code are visible inside the container immediately.
CMD ["bash"]
