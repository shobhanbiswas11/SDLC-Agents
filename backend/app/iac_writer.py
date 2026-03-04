import os
import re

# Points to iac_output

IAC_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'iac_output')
)
LAST_FILE_PATH = os.path.join(IAC_DIR, '.last_generated')

EXTENSIONS = {
    "terraform": "main.tf",
    "kubernetes": "manifest.yaml",
    "ansible": "playbook.yml",
    "docker-compose": "docker-compose.yml",
}

def write_iac(content: str, iac_type: str = "terraform") -> str:
    """Write IaC content to appropriate file, stripping markdown fences."""
    os.makedirs(IAC_DIR, exist_ok=True)

    # Strip markdown code fences
    content = re.sub(r'^```[\w\-]*\s*\n', '', content, flags=re.MULTILINE)
    content = re.sub(r'\n```\s*$', '', content, flags=re.MULTILINE)
    content = content.strip()

    filename = EXTENSIONS.get(iac_type, "main.tf")
    filepath = os.path.join(IAC_DIR, filename)

    with open(filepath, "w") as f:
        f.write(content)

    # Track last written file
    with open(LAST_FILE_PATH, "w") as f:
        f.write(filepath)

    return filepath


def read_iac(filepath: str = None) -> str:
    """Read IaC content from file. Auto-reads last generated file if no path given."""
    try:
        if not filepath:
            with open(LAST_FILE_PATH, "r") as f:
                filepath = f.read().strip()

        with open(filepath, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""