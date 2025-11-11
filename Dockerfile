# Use the official, minimal Python image for efficiency
FROM python:3.11-slim

# Set the working directory for the application
WORKDIR /app

# Set environment variables to optimize Python performance in a container
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# System dependencies for common libraries (e.g., numpy, cryptography)
# The '\' character is used for line continuation in Dockerfiles
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file (to be created next)
COPY requirements.txt .

# Install Python dependencies (uncommented in a later step)
RUN pip install --no-cache-dir -r requirements.txt

# Set a safe, placeholder command for setup phase
CMD ["/bin/bash"]