"""No-op pytest plugin shim.

Some environments auto-load a `devtools.pytest_plugin` entrypoint.
This local module prevents import errors when `backend/devtools` shadows
third-party packages named `devtools`.
"""

