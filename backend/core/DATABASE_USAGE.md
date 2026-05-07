# Database Usage

This agent currently runs stateless — no persistent database is required.
The `core/database_*.py` and `core/providers/database_provider.py` slots in
the project structure are placeholders for future agents that need durable
storage (e.g. session history, scan audit logs).

When a database is added, follow the dependency-resolver pattern: register a
provider in `core/providers/`, wire it through a service in
`core/services/database_service.py`, and expose factory access via
`core/database_factory.py`.
