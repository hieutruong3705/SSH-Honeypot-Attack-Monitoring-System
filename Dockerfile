# Build Stage 1: Frontend
FROM node:18 AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Build Stage 2: Backend (Python)
FROM python:3.10-slim
WORKDIR /app

# Install system dependencies (if any required by SQLite or networking)
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and honeypot source code
COPY backend/ backend/
COPY honeypot/ honeypot/
COPY config.py .
COPY main.py .

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist/ ./frontend/dist/

# Expose ports
EXPOSE 8000
EXPOSE 2222

# Set entrypoint
CMD ["python", "main.py"]
