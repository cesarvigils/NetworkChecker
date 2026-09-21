"""Individual network diagnostic checks.

Each module exposes a single ``get_*``/``run_*`` function that always
returns a dataclass from :mod:`networkchecker.models`, never raises for
expected failure modes (no Wi-Fi, no internet, missing OS tool), and
records what went wrong in the result's ``error`` field instead.
"""
