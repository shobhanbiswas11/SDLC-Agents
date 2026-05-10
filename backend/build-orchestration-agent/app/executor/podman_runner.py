"""
Podman Executor
----------------
Runs builds inside containers using Podman.
Now supports dynamic images and commands based on project type.
"""

import subprocess
import time
import uuid
import os


class PodmanExecutor:
    def __init__(self, image: str = "node:18", build_command: str = "npm run build", install_command: str = "npm install"):
        self.image = image
        self.build_command = build_command
        self.install_command = install_command

    def run_build(self, project_path: str, install_first: bool = True) -> dict:
        """
        Runs the build inside a Podman container.
        Optionally runs install command first, then the build command.
        """
        container_name = f"build-{uuid.uuid4().hex[:8]}"

        if not os.path.exists(project_path):
            raise ValueError(f"Project path does not exist: {project_path}")

        # Build the shell command
        if install_first and self.install_command:
            shell_cmd = f"{self.install_command} && {self.build_command}"
        else:
            shell_cmd = self.build_command

        command = [
            "podman",
            "run",
            "--rm",
            "--name",
            container_name,
            "-v",
            f"{os.path.abspath(project_path)}:/app",
            "-w",
            "/app",
            self.image,
            "sh",
            "-c",
            shell_cmd,
        ]

        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300,  # 5-minute timeout
            )

            end_time = time.time()

            logs = result.stdout + "\n" + result.stderr

            print("\n=== CONTAINER LOGS ===\n")
            print(logs)

            return {
                "success": result.returncode == 0,
                "logs": logs,
                "exit_code": result.returncode,
                "duration": round(end_time - start_time, 2),
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "logs": "Build timed out after 5 minutes",
                "exit_code": -2,
                "duration": 300,
            }

        except Exception as e:
            return {
                "success": False,
                "logs": str(e),
                "exit_code": -1,
                "duration": 0,
            }

    def run_command(self, project_path: str, command: str) -> dict:
        """
        Runs an arbitrary command inside a container (used for applying fixes).
        """
        container_name = f"fix-{uuid.uuid4().hex[:8]}"

        if not os.path.exists(project_path):
            raise ValueError(f"Project path does not exist: {project_path}")

        podman_cmd = [
            "podman",
            "run",
            "--rm",
            "--name",
            container_name,
            "-v",
            f"{os.path.abspath(project_path)}:/app",
            "-w",
            "/app",
            self.image,
            "sh",
            "-c",
            command,
        ]

        try:
            result = subprocess.run(
                podman_cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )

            logs = result.stdout + "\n" + result.stderr

            return {
                "success": result.returncode == 0,
                "logs": logs,
                "exit_code": result.returncode,
            }

        except Exception as e:
            return {
                "success": False,
                "logs": str(e),
                "exit_code": -1,
            }