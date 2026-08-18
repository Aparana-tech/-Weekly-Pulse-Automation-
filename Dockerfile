FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install build tools (needed for compiling some Python packages like numpy/hdbscan)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and requirements.txt first (for better layer caching)
COPY pyproject.toml requirements.txt ./

# Install all dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the API port
EXPOSE 8000

# Start the FastAPI server by default
CMD ["python", "-m", "src.api"]
