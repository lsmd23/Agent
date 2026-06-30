# Docker + WSL setup for Terminal-Bench

Terminal-Bench uses the **Python docker SDK** (`docker.from_env()`), not only the `docker` CLI.

## Current state (T1 probe)

| Check | Status |
|-------|--------|
| `scripts/docker` → Docker Desktop | OK (`docker ps`, `hello-world`) |
| `/var/run/docker.sock` in WSL | **Missing** |
| `tb run` harness trial | Fails: `Error creating docker client` |

## Fix (one-time, Docker Desktop UI)

1. Open **Docker Desktop** on Windows.
2. **Settings → Resources → WSL Integration**.
3. Enable integration for your Ubuntu/WSL distro.
4. Restart WSL: `wsl --shutdown` (from Windows PowerShell), reopen terminal.

## Fix docker.sock permission (required for `tb run`)

WSL integration creates `/var/run/docker.sock` owned by `root:docker`. Your user must be in the **docker** group:

```bash
sudo usermod -aG docker $USER
newgrp docker   # or log out of WSL and reopen
groups          # should include docker
```

Verify Python SDK (what Terminal-Bench uses):

```bash
~/.local/share/uv/tools/terminal-bench/bin/python -c "import docker; docker.from_env().ping(); print('ok')"
```

```bash
source /home/myuser/Agent/scripts/benchmark-env.sh
test -S /var/run/docker.sock && echo "socket ok"
docker ps
python3 -c "import docker; print(docker.from_env().version())"
```

## Until socket exists

- Use **local executable code suite** (`validate_code_fixtures.py`, `run_real_llm_eval.py` on `phase1_code_all.jsonl`).
- T1 adapter is implemented; full TB end-to-end runs after socket is available.

## Environment helper

```bash
source /home/myuser/Agent/scripts/benchmark-env.sh
```

Adds `scripts/` (docker wrapper) and `~/.local/bin` (tb CLI) to PATH.
