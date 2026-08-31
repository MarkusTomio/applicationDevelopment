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

# Copy custom Lonboard wheel containing the shared Earcut worker-pool lifecycle fix
COPY vendor/wheels/lonboard-0.17.0b1-py3-none-any.whl /tmp/lonboard-0.17.0b1-py3-none-any.whl

# Install patched Lonboard wheel without resolving dependencies, which are managed by Pixi
RUN pixi run python -m pip install --no-deps /tmp/lonboard-0.17.0b1-py3-none-any.whl

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
