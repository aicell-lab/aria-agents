# Aria Agents: Empowering Autonomous Scientific Discovery

Aria Agents is a Python package designed to empower autonomous scientific discovery. Built to facilitate collaborative research and exploration, Aria Agents provides a suite of tools and utilities tailored to various scientific tasks, including data retrieval, analysis, visualization, and more. Named after the muse of exploration and discovery, Aria Agents embodies the spirit of scientific inquiry, offering assistance to researchers and enthusiasts alike in navigating the complexities of scientific exploration. Whether you're delving into bioinformatics, computational biology, or any other scientific domain, Aria Agents is your companion in unlocking new insights and pushing the boundaries of knowledge.


## Installation

### Prerequisites

Create a new Conda environment called "aria-agents" with Python version 3.10.13:

```
conda create -n aria-agents python=3.10.13
conda activate aria-agents
```

### Install dependencies

Install packages pandasai and pydantic:

```
pip install pandasai pydantic
```

Install latest version of `schema-agents` (private repo, make sure you have access to that repo):

```
pip install git+https://github.com/aicell-lab/schema-agents.git
```

Install requirements:

```
pip install -r requirements.txt
pip install -e .
```

### `isatools` module installation

The PyPI version of isatools does not install correctly, apparently because of some issue with PyYAML~=5.4.1. The GitHub version is more up to date and the requirements.txt file calls for PyYAML~=6.0.1. You must fork or clone a version of the [[https://github.com/ISA-tools/isa-api][isa-api repo]] and pip install the package from the repo.

### Running the chatbot

Use the following configuration to start the chatbot locally. For VSCode, save it as `aria-agents/.vscode/launch.json`. Fill in `<JWT_SECRET>` with your JWT secret and `<API_KEY>` with your OpenAI API key. If you do not have a JWT secret, any number will do. If you do not have an OpenAI API key, go to [Get a new OpenAI API key](#get-a-new-openai-api-key). To run the configuration in VSCode, select it as a debug configuration under "Run and debug" and run.

```
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: start-server",
            "type": "debugpy",
            "request": "launch",
            "module": "aria_agents",
            "justMyCode": false,
            "env": {
                "JWT_SECRET": "<JWT_SECRET>",
                "OPENAI_API_KEY": "<API_KEY>",
                "OPENAI_API_MODEL": "gpt-4o",
                "BIOIMAGEIO_DEBUG": "true",
    
            },
            "args": [
                "start-server",
                "--port=9527",
                "--login-required"
            ]
        },
    ]
}
```

### Get a new OpenAI API key

To get an OpenAI API key, go to the [[https://platform.openai.com/account/api-keys][OpenAI API keys dashboard]] and click the "Create API Key" button. Copy the API key and paste it into the configuration file.