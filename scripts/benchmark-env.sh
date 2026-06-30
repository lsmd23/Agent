#!/usr/bin/env bash
# Source before Terminal-Bench or benchmark runs in WSL.
#   source scripts/benchmark-env.sh
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -S /var/run/docker.sock ]] && [[ -x /usr/bin/docker ]]; then
  # Prefer Linux docker CLI for compose/build; Windows docker.exe breaks WSL paths.
  export PATH="${HOME}/.local/bin:/usr/bin:/bin:${ROOT}/scripts:${PATH}"
else
  export PATH="${ROOT}/scripts:${HOME}/.local/bin:${PATH}"
fi
if [[ -S /var/run/docker.sock ]]; then
  export DOCKER_HOST="${DOCKER_HOST:-unix:///var/run/docker.sock}"
elif [[ -z "${DOCKER_HOST:-}" ]]; then
  echo "note: /var/run/docker.sock missing; enable Docker Desktop WSL integration (see docs/next_iteration/setup-docker-wsl.md)" >&2
fi
if command -v docker >/dev/null 2>&1; then
  : "docker on PATH: $(command -v docker)"
else
  echo "warning: docker not found; ensure ${ROOT}/scripts/docker exists" >&2
fi
