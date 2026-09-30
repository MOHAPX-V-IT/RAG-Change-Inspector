# Contributing

Keep changes focused and include a failing example for behavior changes. Use synthetic data only.

```shell
python -m venv .venv
python -m pip install -e ".[dev]"
python -m pytest
python -m build
```

Activate the virtual environment before installing (`.venv\Scripts\Activate.ps1` on PowerShell, `source .venv/bin/activate` on macOS/Linux).

The core must remain usable without runtime dependencies. Optional integrations belong in separate modules. Run examples from the repository root. Describe the problem, change and validation in pull requests. This project uses the MIT license.
