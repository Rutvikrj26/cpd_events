# CPD Events CLI

A Python-based CLI tool to streamline local development for the CPD Events project.

## Installation

1.  Navigate to the `cli` directory:
    ```bash
    cd cli
    ```

2.  Install dependencies using Poetry:
    ```bash
    poetry install
    ```

## Usage

Run the CLI using `poetry run python main.py`.

### Commands

#### `local setup`
Installs backend and frontend dependencies and runs database migrations.
```bash
poetry run python main.py local setup
```

#### `local up`
Starts the backend (Django) and frontend (Vite) development servers in the background. Logs are redirected to `.cli/logs/`.
```bash
poetry run python main.py local up
```

#### `local logs`
Participates in tailing the logs of the running services (backend and frontend).
```bash
poetry run python main.py local logs
```

#### `local shell`
Opens the Django shell for the backend.
```bash
poetry run python main.py local shell
```

## Troubleshooting
- Logs are located in `.cli/logs`.
- PIDs of running processes are stored in `.cli/pids`.
