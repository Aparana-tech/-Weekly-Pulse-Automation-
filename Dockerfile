# Stage 1: Build the React Dashboard
FROM node:18 AS frontend-build
WORKDIR /app/dashboard
# Only copy package files first for caching
COPY dashboard/package*.json ./
RUN npm install
# Copy the rest of the dashboard source code
COPY dashboard/ ./
RUN npm run build

# Stage 2: Python API Server
FROM python:3.11-slim
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

# Copy the built React app from Stage 1
COPY --from=frontend-build /app/dashboard/dist /app/dashboard/dist

# Expose the API port
EXPOSE 8000

# Start the FastAPI server by default
CMD ["python", "-m", "src.api"]
