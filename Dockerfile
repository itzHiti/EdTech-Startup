# =============================================================================
# Stage 1: Builder (optional – use if you want a slimmer final image)
# =============================================================================
# We use a single-stage build here for simplicity. For a smaller image you could
# copy only the virtualenv from a builder stage; this Dockerfile keeps it clear.

# Base image: official Python 3.12 slim (Debian-based, smaller than full python).
# "slim" excludes extra tools and keeps the image size down.
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and buffering stdout/stderr.
# This makes logs show up immediately and avoids extra files in the image.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies only if needed.
# libpq-dev is required to build the asyncpg PostgreSQL driver.
# You can remove this if you switch to a pre-built wheel that doesn't need it.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user to run the app (security best practice).
# Running as root inside the container is discouraged in production.
RUN addgroup --system app && adduser --system --group app

# Set the working directory for all following RUN, COPY, CMD instructions.
# Everything will happen under /app.
WORKDIR /app

# Copy only the dependency file first. This layer is cached separately,
# so reinstalling deps happens only when requirements.txt changes.
COPY requirements.txt .

# Install Python dependencies into the system Python (no venv in container).
# --no-cache-dir keeps the image smaller by not storing pip's download cache.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code.
# .dockerignore (if present) will exclude .venv, __pycache__, .git, tests, etc.
COPY . .

# Ensure the app user owns the application directory.
RUN chown -R app:app /app

# Switch to the non-root user. All subsequent commands run as `app`.
USER app

# Expose the port your app listens on. Uvicorn's default is 8000.
# This is metadata only; you still need to publish the port when running the container.
EXPOSE 8000

# Health check: curl the root endpoint. Fails if the app is not responding.
# Adjust the interval/retries if your app starts slowly.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/')" || exit 1

# Run the FastAPI app with Uvicorn.
# - 0.0.0.0: listen on all interfaces so the app is reachable from outside the container.
# - 8000: port (must match EXPOSE).
# - main:app: Python module "main", FastAPI/ASGI app instance "app".
# For production you may want to add: --workers 2 (or use gunicorn + uvicorn workers).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
