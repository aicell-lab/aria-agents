#!/bin/bash

# Create and activate the Conda environment
conda create -n aria-agents python=3.10.13 -y
source activate aria-agents

# Install dependencies
pip install -r requirements_test.txt
pip install -e .

# Prompt the user for the OpenAI API key
read -p "Please enter your OpenAI API key: " api_key

# Create the .env file with the provided API key
cat <<EOT > aria_agents/.env
OPENAI_API_KEY=$api_key
EOT

echo "Setup complete. The OpenAI API key has been saved to aria_agents/.env."