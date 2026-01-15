# wekan Scanner

API utilizer/scanner for wekan.
use Logfire for logging and monitoring - logfire token in .env
## Installation

```bash
uv sync
```

## Usage

```bash
# Test all endpoints
wekan-scanner --url http://localhost:8080 --all

# Test with verbose logging
wekan-scanner --url http://localhost:8080 --all --verbose
```

## Development

```bash
# Run linting
uv run ruff check .

# Run tests
uv run pytest
```
