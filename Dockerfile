# Dockerfile
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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    # Clean up build tools to reduce final image size
    && apt-get purge -y build-essential git \
    && apt-get autoremove -y

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code to the image
COPY src ./src

# Default command to run the agent
CMD ["python3", "-m", "core.agent_core"]