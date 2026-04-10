# Unified Agent API Documentation

This document provides detailed API documentation for the Unified Agent API, implemented using FastAPI. This API exposes HTTP endpoints for managing Temporal agent sessions and for direct RAG-powered chat operations. 

## Overview

### Temporal Agent Sessions Endpoints:
- **`POST /api/workflows`**: Start a Temporal agent session.
- **`POST /api/workflows/{workflow_id}/messages`**: Send a message to a running session.
- **`GET /api/workflows/{workflow_id}/status`**: Poll the status of a session.
- **`DELETE /api/workflows/{workflow_id}`**: Terminate a session.

### Direct RAG-Powered Chat Endpoints:
- **`POST /chat`**: Execute a one-shot RAG-powered chat query about a repository.
- **`POST /stream-chat`**: Perform a RAG-powered chat query with responses streamed as Server-Sent Events (SSE).

---

## Endpoints

### Root Endpoint

#### `GET /`
**Description**:
Root API endpoint to check the status of the API.

**Response**:
- `status`: "ok"
- `message`: "Unified Agent API is running"

---

### List Agents

#### `GET /api/agents`
**Description**:
Retrieve information about available agents.

**Response**:
- `agents`: A list containing agent details such as `id`, `name`, `description`, and available `tools`.

---

### Temporal Agent Endpoints

#### Start Workflow

##### `POST /api/workflows`
**Description**:
Start a new Temporal agent session.

**Request Payload**:
- `agent_id` (string, default: "reviewer"): Identifier for the agent.
- `workspace_path` (string, default: "."): Path to the workspace.

**Response**:
- `workflow_id` (string): Unique identifier for the created workflow.

#### Send Message

##### `POST /api/workflows/{workflow_id}/messages`
**Description**:
Send a user message into the running Temporal workflow session.

**Path Parameters**:
- `workflow_id` (string): ID of the workflow session.

**Request Payload**:
- `message` (string): Message content to send into the workflow.

**Response**:
- `status`: Indicates successful sending of the message.

#### Get Status

##### `GET /api/workflows/{workflow_id}/status`
**Description**:
Poll the workflow for its current status and last response.

**Path Parameters**:
- `workflow_id` (string): ID of the workflow session.

**Response**:
- `status`: Current status and last response of the workflow.

#### Stop Workflow

##### `DELETE /api/workflows/{workflow_id}`
**Description**:
Gracefully stop a running workflow session.

**Path Parameters**:
- `workflow_id` (string): ID of the workflow session.

**Response**:
- `status`: Indicates the workflow session has been stopped.

---

### Direct RAG-Powered Chat Endpoints

#### Chat Endpoint

##### `POST /chat`
**Description**:
Perform a one-shot question-and-answer operation using RAG (Retrieval-Augmented Generation) for a specific repository.

**Request Payload**:
- `repo` (string): Repository GitHub identifier (e.g., "owner/repo").
- `access_token` (string): GitHub access token for authentication.
- `local_path` (string, optional): Local path to the repository.
- `message` (string): User query.

**Response**:
- `answer` (string): AI-generated answer to the query.
- `context_files` (list of strings): List of files considered as context for generating the answer.

#### Stream Chat Endpoint

##### `POST /stream-chat`
**Description**:
Streaming SSE version of the chat endpoint. Provides real-time status updates and AI response chunks.

**Request Payload**:
- Same as `/chat`.

**Response**:
HTTP Streaming using Server-Sent Events (SSE) containing real-time status updates and a stream of AI-generated response chunks.

---

## Utilities and Functions

### `_resolve_temporal_tls_setting()`
**Description**:
Resolve TLS setting for Temporal connectivity based on environment variables.

**Return Type**:
- `bool | None`: Returns `True`, `False`, or `None` based on environment configuration.

### `get_client()`
**Description**:
Connect to the Temporal server (reuse existing connection if available).

**Return Type**:
- `Client`: Temporal client instance.

### `_get_azure_client()`
**Description**:
Build an Azure OpenAI client from environment variables.

**Return Type**:
- `AzureOpenAI`: Azure OpenAI client instance.

### `_normalize_repo_identifier(repo_value)`
**Description**:
Normalize repository identifiers from various formats into a standard "owner/repo" format.

**Parameters**:
- `repo_value` (string): Repository identifier or URL.

**Return Type**:
- `string`: Normalized repository identifier.

---

## Models

### `StartRequest`
**Fields**:
- `agent_id`: Identifier for the agent (default: "reviewer").
- `workspace_path`: Workspace path (default: ".").

### `MessageRequest`
**Fields**:
- `message`: The message to be sent to the workflow.

### `ChatRequest`
**Fields**:
- `repo`: Repository GitHub identifier.
- `access_token`: GitHub access token.
- `local_path`: Local path for the repository if applicable.
- `message`: User query.

### `ChatResponse`
**Fields**:
- `answer`: AI-generated answer.
- `context_files`: List of files used as context.

---

Please ensure the API service is running correctly by accessing the root endpoint or perform initial setup using environment variables for authentication and connection configurations before utilization.