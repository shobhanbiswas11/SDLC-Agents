# 1st AI Agent

## Overview

The **1st AI Agent** is a versatile software tool designed to assist in drafting documentation and providing inline comments using artificial intelligence. It automates tasks related to code documentation, improving efficiency and enhancing collaboration within development teams.

## Features

- **Documentation Drafting**: Automates the generation of comprehensive project documentation.
- **Inline Commenting**: Provides intelligent inline comments to aid code comprehension.
- **Architecture Analysis**: Offers insights into software architecture through diagrams and summaries.
- **File Management**: Facilitates operations like reading, writing, renaming, and deleting files.

## Project Structure

- **Main Modules**:
  - `activities.py`: Core activities performed by the AI agent.
  - `api.py`: API interface for interacting with the agent.
  - `cli.py`: Command-line interface for user interaction.
  - `tools.py`: Utilities and helper functions for various operations.

- **Configuration**:
  - `config/agent.yaml`: Main configuration file for the AI agent.
  - `config/tools/*.yaml`: Configuration files for individual tools.

- **Intelligence**:
  - `intelligence/chat_prompt.py`: Handles conversation prompts.
  - `intelligence/context_selector.py`: Manages context selection.
  - `intelligence/file_ranker.py`: Ranks files based on importance.
  - `intelligence/semantic_ranker.py`: Semantic analysis of text and code.

- **Parsers**:
  - `parsers/ast_graph_builder.py`: Builds AST graphs from codebase.
  - `parsers/metadata_extractor.py`: Extracts metadata from files.
  - `parsers/tree_fetcher.py`: Fetches directory and file structure.

- **Workflow and Execution**:
  - `worker.py`: Worker processes for executing tasks.
  - `workflow.py`: Defines workflows for automated tasks.
  
- **Planning and Resources**:
  - `PLANNING.md`: Planning and strategy documentation.
  - `LICENSE`: License details for the project.
  - `README.md`: Project's readme file (you're reading it now).
  - `requirements.txt`: List of Python dependencies.
  - `pyproject.toml`: Pyproject configuration file.

## Installation

To install the dependencies, ensure you have Python 3.12 or above, then run:

```bash
pip install -r requirements.txt
```

## Usage

### CLI

Execute commands via the command-line interface:

```bash
python cli.py <command> [options]
```

### API

Run the API using Uvicorn:

```bash
uvicorn api:app --reload
```

Access the API at `http://localhost:8000`.

## Configuration

Configure the agent by editing `config/agent.yaml` and respective tool configuration files under `config/tools`.

## Contributing

We welcome contributions! Please refer to `PLANNING.md` for current tasks and future enhancements. Feel free to fork the repository and submit pull requests.

## License

This project is licensed under the terms specified in the `LICENSE` file.

## Contact

For support or inquiries, please reach out through [GitHub Issues](https://github.com/1st-ai-agent/issues) or the project repository.

---

This project leverages AI capabilities to enhance productivity and ease the process of maintaining robust documentation and code-awareness. Whether you're managing large-scale projects or looking to streamline your documentation tasks, the 1st AI Agent is designed to adapt and deliver.