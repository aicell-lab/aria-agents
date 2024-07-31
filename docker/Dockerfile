# Use an image with Python 3.11
FROM python:3.11-slim

# Install git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -r aria_agents && useradd -r -g aria_agents aria_agents

# Upgrade pip
RUN pip install --upgrade pip

# Copy the repository to the image
COPY . /app/aria-agents/

# Set the working directory
WORKDIR /app/aria-agents

# Remove all files matching .gitignore patterns
RUN git clean -fdX

# Remove the .git directory
RUN rm -rf .git

# Install the required Python packages
RUN pip install -r requirements.txt
RUN pip install .

# Change ownership of the application directory to the non-root user
RUN chown -R aria_agents:aria_agents /app/

# Switch to the non-root user
USER aria_agents

# Expose port
EXPOSE 9520

# Start a new hypha server
ENTRYPOINT ["python", "-m", "aria_agents", "start-server", "--port", "9520"]
