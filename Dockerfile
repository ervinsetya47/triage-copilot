# Minimal image for hosting server.py (e.g. Fly.io free tier).
# No dependencies to install: Python 3 stdlib only.
FROM python:3.12-slim
WORKDIR /app
COPY . /app
# Hosting platforms set $PORT; server.py reads it (default 8000).
# Fly.io / Render bind 0.0.0.0 automatically via the $PORT they assign;
# set HOST=0.0.0.0 in the platform's environment variables.
CMD ["python3", "server.py"]
