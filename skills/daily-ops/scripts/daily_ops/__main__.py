"""Allow python -m daily_ops when the scripts directory is on PYTHONPATH."""

from .cli import main

raise SystemExit(main())
