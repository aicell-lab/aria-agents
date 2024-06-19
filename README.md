# Aria Agents: Empowering Autonomous Scientific Discovery

Aria Agents is a Python package designed to empower autonomous scientific discovery. Built to facilitate collaborative research and exploration, Aria Agents provides a suite of tools and utilities tailored to various scientific tasks, including data retrieval, analysis, visualization, and more. Named after the muse of exploration and discovery, Aria Agents embodies the spirit of scientific inquiry, offering assistance to researchers and enthusiasts alike in navigating the complexities of scientific exploration. Whether you're delving into bioinformatics, computational biology, or any other scientific domain, Aria Agents is your companion in unlocking new insights and pushing the boundaries of knowledge.


## Installation

### Prerequisites
```
conda create -n aria-agents python=3.10.13
conda activate aria-agents
```

### `isatools` module installation

The PyPI version of isatools does not install correctly, apparently because of some issue with PyYAML~=5.4.1. The GitHub version is more up to date and the requirements.txt file calls for PyYAML~=6.0.1. You must fork or clone a version of the [[https://github.com/ISA-tools/isa-api][isa-api repo]] and pip install the package from the repo.
```
```