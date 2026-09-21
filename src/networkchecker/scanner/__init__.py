"""Optional background stability scanner.

This is the "second package" the README describes: a downtime/
disconnection scanner that runs in a background thread, logs connectivity
events to a local SQLite database, and can produce a weekly stability
summary. It is entirely opt-in — nothing here runs unless the CLI's
``scanner start`` command or the GUI's "Enable Scanner" checkbox is used.
"""
