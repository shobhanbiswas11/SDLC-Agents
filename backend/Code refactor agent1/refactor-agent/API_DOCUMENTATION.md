# Code Refactoring Agent API Documentation

## Activities

### Azure OpenAI Client

**Function: `_get_openai_client`**  
Builds or returns a cached Azure OpenAI client.

- **Parameters**: None
- **Returns**: `AzureOpenAI` client instance.

### Activities

1. **llm_call**
   - **Definition**: An activity that sends messages to Azure OpenAI and returns tool calls or text back.
   - **Parameters**: 
     - `messages` (list[dict]): List of message dictionaries.
     - `tool_schemas` (list[dict]): List of tool schemas (partially in code, cut-off, but assumed based on context).

2. **run_tool**
   - **Definition**: An activity that finds the appropriate tool handler and executes it.
   - **Parameters**: Not provided in the snippet.

## FastAPI Endpoints

### Health Check

- **GET `/`** 
  - **Description**: Verifies server health and service availability.
  - **Parameters**: None
  - **Response**: Health status of the server.

### Agents List

- **GET `/api/agents`**
  - **Description**: Lists available agents.
  - **Parameters**: None
  - **Response**: JSON object with a list of agents.

### Start a New Session

- **POST `/api/workflows`**
  - **Description**: Initiates a new workflow session.
  - **Parameters**: 
    - Request body: configuration for the session (specific fields are not provided in the snippet).
  - **Response**: Session ID and initial status.

### Send a Message

- **POST `/api/workflows/{id}/messages`**
  - **Description**: Sends a message to an ongoing session.
  - **Parameters**:
    - `id` (str): Session identifier.
    - Request body: Message content to be sent.
  - **Response**: Message acceptance status or error.

### Poll for Status

- **GET `/api/workflows/{id}/status`**
  - **Description**: Retrieves the current status of the specified session.
  - **Parameters**:
    - `id` (str): Session identifier.
  - **Response**: JSON object with session status and possibly result data.

### Stop a Session

- **DELETE `/api/workflows/{id}`**
  - **Description**: Terminates the specified session.
  - **Parameters**:
    - `id` (str): Session identifier.
  - **Response**: Termination confirmation or error.

## Configuration Utility

### Configuration Loader

**Module: `config_loader.py`**

- **Function: `load_agent_config`**  
  Loads the agent configuration from `agent.yaml`.

  - **Parameters**: None
  - **Returns**: Dictionary with system prompt and configuration details.

- **Function: `yaml_tool_to_openai_schema`**  
  Converts a tool's YAML data into an OpenAI function calling format.

  - **Parameters**:
    - `tool_data` (dict): A dictionary containing YAML tool information.
  - **Returns**: Dictionary formatted for OpenAI tools.

- **Function: `load_tool_schemas`**  
  Loads tool schemas from YAML files given tool names.

  - **Parameters**:
    - `tool_names` (list of str): The tool names to load.
  - **Returns**: List of dictionaries containing tool schemas.

## Semantic Safety

**Module: `semantic_safety.py`**

- **Function: `load_refactor_policy`**  
  Loads repository refactor policies from provided file paths.

  - **Parameters**:
    - `workspace_path` (str): The workspace directory path.
  - **Returns**: Dictionary of the loaded policy settings.

## Tools

**Module: `tools.py`**

- **Description**: Contains all tool handler functions that execute the tools. Each tool is invoked based on AI selection and handles its own logic.

## Worker

**Module: `worker.py`**

- **Purpose**: Boots the Temporal Worker, registering the workflow and activities, and listens on the specified task queue.

- **Function: `main`**  
  Starts the worker, registering tasks for execution.

  - **Parameters**: None
  - **Returns**: Run status and listening loop for task queue.

## Workflow

**Module: `workflow.py`**

- **Purpose**: Contains the Temporal Workflow for the Code Refactoring Agent. Follows a ReAct loop for decision-making and execution readiness.

### Core Functions

- **Function: `_augment_message_with_github_paths`**  
  Augments messages with GitHub paths to improve file tool accuracy.

  - **Parameters**:
    - `message` (str): The message text to augment.
    - `workspace_path` (str, optional): Defaults to `'.'`.
  - **Returns**: Augmented message string.

This documentation offers an overview of the API, functions, and workflow processes managed by the Code Refactoring Agent Server.