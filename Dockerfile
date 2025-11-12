# Use the official, minimal Python image for efficiency
FROM python:3.11-slim

# Set the working directory for the application
WORKDIR /app

# Set environment variables to optimize Python performance in a container
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# System dependencies for common libraries (e.g., numpy, cryptography)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file (to be created next)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# CRITICAL SECURITY FIX: Create a dedicated, non-root user for the Agent
RUN useradd -ms /bin/bash appuser

# Set permissions and switch to the non-root user
# Grant ownership of /app to appuser so Python can run
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Set a safe, placeholder command for setup phase
CMD ["/bin/bash"]