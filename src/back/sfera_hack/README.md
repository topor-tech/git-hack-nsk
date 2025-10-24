## Local run

    uv pip compile pyproject.toml --output-file requirements.txt
    uv pip install -r requirements.txt --system

    uv sync
    uv run fastapi dev sfera_hack\app.py
