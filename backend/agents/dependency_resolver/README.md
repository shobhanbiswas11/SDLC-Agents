# Dependency Resolver Agent

Agentic system for resolving software package dependencies from `package.json` and `requirements.txt` files.

## Overview

This agent:
- Parses dependency manifests (npm, pip)
- Builds complete dependency graphs (including transitive dependencies)
- Detects version conflicts
- Iteratively resolves conflicts
- Validates installability
- Supports human-in-the-loop decision making
- Persists state as JSON for resumability

## Architecture

```
DependencyResolverAgent
├── _parse_dependencies()          # Parse package.json or requirements.txt
├── _build_dependency_graph()      # Fetch transitive deps from registries
├── _detect_conflicts()             # Identify version mismatches
├── _resolve_conflicts()            # Find compatible versions
├── _validate_resolution()          # Check installability
└── execute()                       # Main loop: Parse → Graph → Detect → Resolve → Validate → Iterate
```

## Usage

### Basic Resolution

```python
from agents.dependency_resolver.schemas import DependencyInput

payload = DependencyInput(
    file_type="package.json",
    content='{"dependencies": {"express": "^4.0.0", "lodash": "^4.17.0"}}',
    auto_resolve=True
)

response = await execute_agent(payload)
```

### Resume Previous Session

```python
payload = DependencyInput(
    file_type="package.json",
    content=previous_content,
    session_id="abc-123",  # Resume this session
    auto_resolve=True
)
```

### Require Human Input

When conflicts exist and multiple resolutions are valid, the agent can pause and ask for guidance:

```python
payload = DependencyInput(
    file_type="requirements.txt",
    content=content,
    auto_resolve=False  # Pause for human decisions
)

response = await execute_agent(payload)

if response.status == "AWAITING_INPUT":
    # Present options to user
    print(response.human_decision_needed)
    print(response.decision_options)
    # Wait for user choice, then resume with same session_id
```

## State Persistence

Session state is saved to `state/<session_id>.json` after each step:

```json
{
  "session_id": "abc123",
  "file_type": "package.json",
  "input_dependencies": { "express": "^4.0.0" },
  "dependency_graph": { ... },
  "conflicts": [],
  "resolution": { "express": "4.18.2" },
  "validation_passed": true,
  "iteration": 2,
  "status": "DONE",
  "created_at": "2024-01-15T10:00:00",
  "updated_at": "2024-01-15T10:05:00"
}
```

This allows:
- **Resumability**: Continue from last checkpoint if process fails
- **Idempotency**: Replay decisions consistently
- **Observability**: Track resolution progress iteration-by-iteration

## Endpoints

### POST `/dependency-resolver/resolve`

Resolve dependencies in a manifest file.

**Request:**
```json
{
  "file_type": "package.json",
  "content": "...",
  "auto_resolve": true,
  "session_id": null
}
```

**Response:**
```json
{
  "status": "DONE",
  "session_id": "abc-123",
  "resolved_dependencies": {
    "express": "4.18.2",
    "lodash": "4.17.21"
  },
  "dependency_graph": { ... },
  "conflicts": [],
  "validation": {
    "installable": true,
    "issues": []
  },
  "iteration": 2,
  "message": "✓ Dependency resolution successful!"
}
```

### POST `/dependency-resolver/resume`

Resume a previous resolution session.

### GET `/dependency-resolver/health`

Health check endpoint.

## Implementation Status

### ✅ Completed
- [x] Schemas (input/output models)
- [x] Router with endpoints
- [x] Parsing for package.json and requirements.txt
- [x] State persistence (JSON-based)
- [x] Main execution loop structure
- [x] Error handling and logging

### 🚧 In Progress / TODO
- [ ] Registry integration (npm, PyPI)
- [ ] Transitive dependency fetching
- [ ] Conflict detection logic
- [ ] Resolution strategies (upgrade, downgrade, replace)
- [ ] Validation engine
- [ ] Iterative loop implementation
- [ ] Human-in-the-loop decision framework
- [ ] Caching for registry calls
- [ ] Tests

## Next Steps

1. **Implement registry clients**: Create NPM and PyPI registry fetchers
2. **Build dependency graph**: Fetch transitive dependencies recursively
3. **Implement conflict detection**: Find incompatible version constraints
4. **Implement resolution engine**: Use constraints to find compatible versions
5. **Implement validation**: Simulate installation to verify resolution
6. **Add human-in-the-loop**: Present options when multiple solutions exist
7. **Add caching**: Cache registry calls for performance
8. **Test thoroughly**: Unit tests, integration tests, end-to-end tests

## Configuration

The agent looks for state files in the `state/` directory (created automatically on first run).

Future: Add config file support for:
- Registry URLs
- Cache TTL
- Timeout settings
- Preference rules
