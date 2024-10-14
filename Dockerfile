# Use an image with Python 3.11
FROM python:3.11-slim

# Install git and other system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -r aria_agents && useradd -r -g aria_agents aria_agents

# Upgrade pip
RUN pip install --upgrade pip

# Copy the repository to the image
COPY . /app/

# Create logs directory and set permissions
RUN mkdir -p /app/logs && chown -R aria_agents:aria_agents /app

# Set the working directory
WORKDIR /app/

# Add /app to the list of safe directories for Git
RUN git config --global --add safe.directory /app

# Remove all files matching .gitignore patterns and .git directory
RUN git clean -fdX && rm -rf .git

# Install the required Python packages
RUN pip install -r requirements.txt
RUN pip install fastapi hypha_rpc uvicorn .

# Change ownership of the application directory to the non-root user
RUN chown -R aria_agents:aria_agents /app/

# Switch to the non-root user
USER aria_agents

# Expose the necessary port
EXPOSE 9520

# Entry point for the application
ENTRYPOINT ["python", "-m", "aria_agents", "connect-server"]