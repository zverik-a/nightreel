"""Single source of truth for the project's identity.

To rename the project, run ``python scripts/rename.py NEWNAME`` instead of editing by hand.
"""

APP_NAME = "nightreel"
__version__ = "0.1.0"

ENV_PREFIX = APP_NAME.upper().replace("-", "_") + "_"
USER_AGENT = f"{APP_NAME}/{__version__}"
