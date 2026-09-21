"""``python -m networkchecker`` — launches the GUI if available, else CLI help.

The packaged Windows .exe/.msi builds point directly at ``gui.main`` (see
packaging/pyinstaller/NetworkChecker.spec), so this entry point mostly
matters for running from source.
"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from . import gui
    except ImportError:
        from .cli import main as cli_main

        print(
            "Tkinter is not available in this Python environment, so the GUI "
            "can't start. Falling back to the command-line interface.\n",
            file=sys.stderr,
        )
        return cli_main(["--help"])
    return gui.main()


if __name__ == "__main__":
    sys.exit(main())
