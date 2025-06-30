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
COPY --from=ghcr.io/astral-sh/uv:0.7.17 /uv /uvx /bin/

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Sync the project into a new environment, asserting the lockfile is up to date
# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Run backup-mongodb by default
CMD ["backup-mongodb"]
