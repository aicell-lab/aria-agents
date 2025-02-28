# Aria Agents: Empowering Autonomous Scientific Discovery

Aria Agents is a Python package designed to empower autonomous scientific discovery. Built to facilitate collaborative research and exploration, Aria Agents provides a suite of tools and utilities tailored to various scientific tasks, including data retrieval, analysis, visualization, and more. Named after the muse of exploration and discovery, Aria Agents embodies the spirit of scientific inquiry, offering assistance to researchers and enthusiasts alike in navigating the complexities of scientific exploration. Whether you're delving into bioinformatics, computational biology, or any other scientific domain, Aria Agents is your companion in unlocking new insights and pushing the boundaries of knowledge.

## Automated Installation

To install Aria Agents automatically, run the following command:

```bash
bash setup_dev.sh
```

## Manual Installation

If you prefer to install Aria Agents manually, follow the steps below:

### Prerequisites

Create a new Conda environment called "aria-agents" with Python version 3.11:

```
conda create -n aria-agents python=3.11
conda activate aria-agents
```

### Install dependencies

```
pip install -r requirements_test.txt
pip install -e .
```

### Configuration

Create a file named `.env` in `aria_agents/` with the following content:

```
OPENAI_API_KEY=<your_openai_api_key>
```

Replace `<your_openai_api_key>` with your OpenAI API key (or get a new one at the [OpenAI API keys dashboard](https://platform.openai.com/account/api-keys)).

## Running Aria Agents

### Running in VSCode

Go to "Run and Debug" and select "Python: start-server" as the debug configuration. Press run.