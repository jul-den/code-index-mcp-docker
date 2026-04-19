# Use lightweight Python image
FROM python:3.11-slim

# Install git (for code analysis)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency list and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy necessary source files
COPY src/ ./src/
COPY run.py .
COPY LICENSE .

# Set Python path
ENV PYTHONPATH="/app:/app/src"
ENV PYTHONUNBUFFERED=1

# Run MCP tool
ENTRYPOINT ["python", "/app/run.py"]
