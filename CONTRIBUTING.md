# Contributing to backup_mongodb

Thank you for your interest in contributing to backup_mongodb! This document provides guidelines and instructions to make the contribution process smooth and effective.

## Types of Contributions Welcome

-   Bug fixes
-   Feature enhancements
-   Documentation improvements
-   Test additions

## Development Setup

### Prerequisites

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. To start developing:

1. Install uv using the [recommended method](https://docs.astral.sh/uv/installation/) for your operating system
2. Clone this repository: `git clone https://github.com/natelandau/backup_mongodb`
3. Navigate to the repository: `cd backup_mongodb`
4. Install dependencies with uv: `uv sync`
5. Activate your virtual environment: `source .venv/bin/activate`
6. Install pre-commit hooks: `pre-commit install --install-hooks`

### Running Tasks

We use [Duty](https://pawamoy.github.io/duty/) as our task runner. Common tasks:

-   `duty --list` - List all available tasks
-   `duty lint` - Run all linters
-   `duty test` - Run all tests
-   `duty dev-clean` - Clean the development environment
-   `duty dev-setup` - Set up the development environment

## Local Development Environment

To set up a local development environment, run `duty dev-setup`. This will create a development environment in the `.dev` directory.

```
.dev
├── backups
└── logs
```

Use the directory structure to test the development environment.

### Testing the Docker Entrypoint

Docker is configured entirely with environment variables. To test the entrypoint follow these steps:

1. Run `duty dev-setup` to create the development environment. This will create a `.dev/` folder and create a `.env` file at the project root.
2. Edit the `.env` file to configure the environment
3. Add any secrets to a `.env.secrets` file
4. Run `uv run -m backup_mongodb.entrypoint` to run the entrypoint; or
5. Run `docker compose up --build` to run the docker container

## Development Guidelines

When developing for backup_mongodb, please follow these guidelines:

-   Write full docstrings
-   All code should use type hints
-   Write unit tests for all new functions
-   Write integration tests for all new features
-   Follow the existing code style

## Commit Process

1. Create a branch for your feature or fix
2. Make your changes
3. Ensure code passes linting with `duty lint`
4. Ensure tests pass with `duty test`
5. Commit using [Commitizen](https://github.com/commitizen-tools/commitizen): `cz c`
6. Push your branch and create a pull request

We use [Semantic Versioning](https://semver.org/) for version management.
