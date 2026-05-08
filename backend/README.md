# GENAICOE Agents Backend

FastAPI-based backend for the GENAICOE multi-cloud agents platform, starting with the Dependency Resolver Agent.

## Quick Start

### 1. Setup Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Server

```bash
# With auto-reload (development)
uvicorn main:app --reload

# Or using the if __name__ == "__main__" block:
python main.py
```

The server will start at: **http://localhost:8000**

### 4. Access Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Project Structure

```
backend/
├── main.py                          # FastAPI app entry point
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template (create .env)
├── agents/
│   └── dependency_resolver/         # Dependency resolver agent
│       ├── __init__.py             # FastAPI router and endpoints
│       ├── agent.py                # Core agent logic
│       ├── schemas.py              # Pydantic models
│       ├── initialization.py       # Startup/shutdown logic
│       └── README.md               # Agent documentation
├── core/                            # Shared infrastructure (planned)
│   ├── config/                      # Configuration management
│   ├── providers/                   # Cloud provider implementations
│   ├── services/                    # Shared services (LLM, DB, etc.)
│   ├── schemas/                     # Shared Pydantic models
│   ├── exceptions.py               # Custom exceptions
│   └── logging.py                  # Logging configuration
├── state/                           # Session state storage (JSON files)
└── logs/                            # Application logs (created on first run)
```

## Dependency Resolver Agent

The first agent in the platform. See [agents/dependency_resolver/README.md](./agents/dependency_resolver/README.md) for detailed documentation.

### Quick Example

```bash
curl -X POST http://localhost:8000/dependency-resolver/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "file_type": "package.json",
    "content": "{\"dependencies\": {\"express\": \"^4.0.0\"}}",
    "auto_resolve": true
  }'
```

## Environment Setup

Create a `.env` file in the `backend/` directory:

```bash
# Copy from template
cp .env.example .env

# Then edit .env with your settings
```

**Example .env:**
```
ENVIRONMENT=development
LOG_LEVEL=INFO

# Cloud provider credentials (when implementing)
# AZURE_OPENAI_API_KEY=xxx
# AWS_ACCESS_KEY_ID=xxx
# GCP_PROJECT_ID=xxx
```

## Development

### Running Tests

```bash
pytest -v
pytest -v --cov=agents  # With coverage
```

### Code Formatting

```bash
black .
flake8 .
mypy .
```

### Creating a New Agent

1. **Create agent directory:**
   ```bash
   mkdir agents/my_agent
   ```

2. **Add required files:**
   ```bash
   touch agents/my_agent/{__init__.py,agent.py,schemas.py,initialization.py}
   ```

3. **Implement using the template:**
   - Use `dependency_resolver` as a reference
   - Follow the structure in [../agents.md](../agents.md)

4. **Register in main.py:**
   ```python
   from agents.my_agent import my_agent_router
   app.include_router(my_agent_router)
   ```

## API Endpoints

### Health Check
- `GET /` - Root endpoint
- `GET /health` - Health check

### Dependency Resolver
- `POST /dependency-resolver/resolve` - Resolve dependencies
- `POST /dependency-resolver/resume` - Resume a session
- `GET /dependency-resolver/health` - Agent health

See [agents/dependency_resolver/README.md](./agents/dependency_resolver/README.md) for detailed endpoint documentation.

## Next Steps

### Phase 1: Core Infrastructure ✅ (In Progress)
- [x] FastAPI setup
- [x] Agent scaffolding template
- [x] Dependency Resolver agent structure
- [ ] Unit tests for parsing
- [ ] Integration tests

### Phase 2: Registry Integration (Next)
- [ ] NPM registry client
- [ ] PyPI registry client
- [ ] Caching layer
- [ ] Registry error handling

### Phase 3: Resolution Engine (Next)
- [ ] Dependency graph building
- [ ] Conflict detection
- [ ] Resolution strategies
- [ ] Validation engine

### Phase 4: Features
- [ ] Human-in-the-loop UI integration
- [ ] Multi-ecosystem resolution
- [ ] Security checks
- [ ] Lockfile generation

### Phase 5: Infrastructure
- [ ] Database support (PostgreSQL)
- [ ] Vector DB support (AstraDB, Azure AI Search)
- [ ] LLM provider integrations (Azure, AWS, GCP)
- [ ] Docker containerization
- [ ] CI/CD pipeline

## Troubleshooting

### Port 8000 Already in Use

```bash
# Find and kill process using port 8000
lsof -i :8000
kill -9 <PID>

# Or use a different port
uvicorn main:app --reload --port 8001
```

### Import Errors

```bash
# Ensure you're in the backend directory
cd backend

# Ensure virtual environment is activated
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows
```

### Module Not Found

```bash
# Reinstall requirements
pip install -r requirements.txt --force-reinstall

# Add backend to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

## Deployment

### Docker

```bash
docker build -t genaicoe-agents .
docker run -p 8000:8000 --env-file .env genaicoe-agents
```

### Cloud Platforms

- **Azure**: App Service or Container Instances
- **AWS**: Lambda, ECS, or EC2
- **GCP**: Cloud Run or App Engine

See [../DEPLOYMENT.md](../DEPLOYMENT.md) for detailed deployment guides.

## Contributing

1. Follow the agent structure in [../agents.md](../agents.md)
2. Write tests for new features
3. Use type hints everywhere
4. Format code with `black`
5. Check style with `flake8` and `mypy`

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [GENAICOE Architecture Guide](../agents.md)
- [Dependency Resolver Agent](./agents/dependency_resolver/README.md)
