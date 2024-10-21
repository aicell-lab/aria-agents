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

```
pip install -r requirements_test.txt
pip install -e .
```

### Running Aria Agents

Use the following configuration to start Aria Agents locally. For VSCode, save it as `aria-agents/.vscode/launch.json`. Fill in `<JWT_SECRET>` with your JWT secret and `<API_KEY>` with your OpenAI API key (or get a new one at the [OpenAI API keys dashboard](https://platform.openai.com/account/api-keys). If you do not have a JWT secret, any integer will do. To run the configuration in VSCode, select it as a debug configuration under "Run and debug" and press run.

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
                "OPENAI_API_MODEL": "gpt-4o-2024-08-06",
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
