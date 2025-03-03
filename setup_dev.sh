#!/bin/bash

# Create and activate the Conda environment
conda create -n aria-agents python=3.11 -y
source activate aria-agents

# Install dependencies
pip install -r requirements_test.txt
pip install -e .

# Prompt the user for the OpenAI API key
read -s -p "Please enter your OpenAI API key: " api_key
echo
read -s -p "Please enter an aria-agents workspace token (or press enter to skip): " workspace_token
echo

# Create the .env file with the provided API key
cat <<EOT > aria_agents/.env
BIOIMAGEIO_LOGIN_REQUIRED=true
OPENAI_API_KEY=$api_key
EOT

# Append the workspace token if provided
if [ -n "$workspace_token" ]; then
    echo "WORKSPACE_TOKEN=$workspace_token" >> aria_agents/.env
fi

cp aria_agents/.env tests/

echo "Setup complete. The OpenAI API key has been saved to aria_agents/.env."