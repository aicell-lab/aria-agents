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

# Set the working directory
WORKDIR /app/

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

# Entry point for registering the service to an existing Hypha server
ENTRYPOINT ["python", "-m", "aria_agents", "register-service", "--server_url", "$SERVER_URL", "--workspace_name", "$WORKSPACE_NAME", "--client_id", "$CLIENT_ID", "--service_id", "$SERVICE_ID", "--ui_path", "/app/ui"]

# Start a new hypha server
CMD python -m hypha_rpc.utils.serve main:app \
     --id=aria-agents-service \
     --name="Aria Agents Service" \
     --server-url=https://hypha.aicell.io \
     --workspace=aria-agents \
     --login