#!/usr/bin/env python
"""Wrapper to run the `test_statistics_user_retrieve.py` script inside the project's Docker `web` service.

Usage (from repo root):
  python skyvan/scripts/run_test_in_docker.py

If this script is executed already inside a container (detected via `/.dockerenv` or
`IN_DOCKER=1`), it will import and run the test script directly.
"""
import os
import sys
import subprocess

SCRIPT_PATH = "skyvan/scripts/test_statistics_user_retrieve.py"


def inside_docker():
    if os.environ.get("IN_DOCKER") == "1":
        return True
    return os.path.exists("/.dockerenv")


def run_inside_container():
    # Run via docker compose using the 'web' service defined in docker-compose.yml
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    compose_file = os.path.join("skyvan", "docker-compose.yml")
    # When using the compose file located in `skyvan/`, the service's
    # `/app` will contain the contents of that directory. The test script
    # inside the container will be at `/app/scripts/test_statistics_user_retrieve.py`.
    # Use forward slashes (POSIX) explicitly to avoid Windows backslashes leaking into
    # the container command on Windows hosts.
    script_in_container = "/app/scripts/test_statistics_user_retrieve.py"

    variants = [
        ["docker", "compose", "-f", compose_file, "run", "--rm", "web", "python", script_in_container],
        ["docker-compose", "-f", compose_file, "run", "--rm", "web", "python", script_in_container],
    ]

    last_err = None
    for cmd in variants:
        print("Trying:", " ".join(cmd))
        try:
            subprocess.check_call(cmd, cwd=repo_root)
            return
        except FileNotFoundError as e:
            # docker or docker-compose binary not found
            last_err = e
            print(f"Executable not found: {cmd[0]}")
            continue
        except subprocess.CalledProcessError as e:
            last_err = e
            print(f"Command failed with exit code {e.returncode}")
            continue

    print("All docker compose attempts failed.")
    if isinstance(last_err, FileNotFoundError):
        print("Docker CLI not found. Please install Docker and ensure 'docker' or 'docker-compose' is on PATH.")
    else:
        print("Last error:", last_err)
    sys.exit(1)


def run_direct():
    # Import and execute the script module directly
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    mod_path = SCRIPT_PATH.replace("/", ".").replace(".py", "")
    module = __import__(mod_path, fromlist=["*"])
    if hasattr(module, "main"):
        module.main()
    else:
        print("Test script does not expose main(); running as script")
        subprocess.check_call([sys.executable, SCRIPT_PATH])


def main():
    if inside_docker():
        print("Detected container environment — running test script directly inside container.")
        run_direct()
    else:
        print("Not inside container — will run test script inside Docker 'web' service.")
        run_inside_container()


if __name__ == "__main__":
    main()
