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
    # FIX #7: Explicitly uninstall build-tools in the same layer to reduce final image size
    && apt-get purge -y build-essential git \
    && apt-get autoremove -y

# Copy the requirements file (to be created next)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code to the image
# Note: Source code will be mounted at runtime via docker-compose volume for persistence,
# but a base copy is useful for initial build and if running without a mount.
COPY src ./src

# Default command to run the agent
CMD ["python", "src/core/agent_core.py"]