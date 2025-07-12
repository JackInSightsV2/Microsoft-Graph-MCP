# Microsoft Graph MCP Server - Python SDK Version
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    apt-transport-https \
    lsb-release \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user
RUN useradd --create-home --shell /bin/bash app

# Copy the application
COPY graph_mcp/ ./graph_mcp/
COPY pyproject.toml .

# Change ownership of /app to the app user AFTER copying files
RUN chown -R app:app /app

USER app

# Set environment variables
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
ENV LOG_FILE=/tmp/graph_mcp.log

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import graph_mcp; print('OK')" || exit 1

# Expose port (though MCP uses stdio, this is for future HTTP transport)
EXPOSE 8080

# Run the MCP server
CMD ["python", "-m", "graph_mcp.main"] 