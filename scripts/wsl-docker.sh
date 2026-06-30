#!/usr/bin/env bash
# Invoke Docker Desktop from WSL when the Linux docker CLI is not on PATH.
set -euo pipefail
DOCKER_EXE="/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe"
if [[ ! -x "$DOCKER_EXE" ]]; then
  echo "Docker Desktop binary not found at: $DOCKER_EXE" >&2
  exit 127
fi
exec "$DOCKER_EXE" "$@"
