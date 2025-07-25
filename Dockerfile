FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Create a non-root user
RUN useradd -m -u 1000 mdfmcp && chown -R mdfmcp:mdfmcp /app
USER mdfmcp

# Expose port for HTTP transport (optional)
EXPOSE 8000

# Default command
CMD ["python", "-m", "mdfmcp.server"] 