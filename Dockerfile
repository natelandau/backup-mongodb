FROM mongo:8.0.10-noble

# Set labels
LABEL org.opencontainers.image.source=https://github.com/natelandau/backup-mongodb
LABEL org.opencontainers.image.description="Backup MongoDB databases"
LABEL org.opencontainers.image.licenses=MIT
LABEL org.opencontainers.image.url=https://github.com/natelandau/backup-mongodb
LABEL org.opencontainers.image.title="Backup MongoDB"

# Install Apt Packages
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    ca-certificates \
    curl \
    tar \
    tzdata \
    wget

# Set timezone
ENV TZ=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ >/etc/timezone

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.8.8 /uv /uvx /bin/

# Set the working directory
WORKDIR /app

# Copy the project into the image
COPY uv.lock pyproject.toml README.md LICENSE ./
COPY src/ ./src/

RUN uv sync --locked --no-dev --no-cache

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Run backup-mongodb by default
CMD ["backup-mongodb"]
