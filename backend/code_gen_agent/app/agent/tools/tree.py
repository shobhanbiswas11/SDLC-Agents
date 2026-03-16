from app.agent.schemas.spec import Spec


def generate_folder_tree(spec: Spec) -> list[str]:
    base = spec.project_name or "generated_project"

    files = [
        f"{base}/pyproject.toml",
        f"{base}/README.md",
        f"{base}/.gitignore",
        f"{base}/src/main.py",
        f"{base}/tests/test_health.py",
    ]

    return files