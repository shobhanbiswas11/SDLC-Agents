import tempfile
import shutil
from git import Repo


def clone_repository(repo_url: str) -> str:
    """
    Clone repository into a temporary directory.
    Returns the local path.
    """

    temp_dir = tempfile.mkdtemp()

    try:
        Repo.clone_from(repo_url, temp_dir, depth=1)
        return temp_dir
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise Exception(f"Failed to clone repository: {str(e)}")