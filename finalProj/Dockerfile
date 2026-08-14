# Start from Ubuntu Noble with fixed Pixi version
FROM ghcr.io/prefix-dev/pixi:0.69.0-noble

# Use /app as working directory inside container
WORKDIR /app

# Store container Pixi environment outside /app because local app/ directory is mounted over /app when container starts
RUN pixi config set --global detached-environments true

# Copy dependency definitions separately so Docker can cache installed environment when only notebook code changes
COPY app/pixi.toml app/pixi.lock ./

# Install exactly dependency versions recorded in pixi.lock
RUN pixi install --locked

# Disable Marimo update check
ENV MARIMO_SKIP_UPDATE_CHECK=1

# Prevent runtime Pixi commands from modifying an inconsistent lockfile
ENV PIXI_LOCKED=true

# Document port used by Marimo
EXPOSE 8080

# Start notebooks in editing mode
# --headless prevents browser-launch attempts inside container
# --no-token is acceptable because Compose exposes the port only locally
CMD ["pixi", "run", "marimo", "edit", "--headless", "--host", "0.0.0.0", "--port", "8080", "--no-token"]
