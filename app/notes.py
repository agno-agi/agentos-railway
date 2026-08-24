"""
Shared Notes
============

A shared notebook for the platform's components
"""

from agno.fs import FileSystem
from agno.tools import Toolkit

from db import get_postgres_db

NOTES_NAMESPACE = "shared-notes"

notes = FileSystem(get_postgres_db(), namespace=NOTES_NAMESPACE)

SHARED_NOTES_INSTRUCTIONS = """\
The shared notebook is how this platform remembers things across people and \
components. Read it before you answer a question about what the team has \
decided, and file what you learn so the next reader does not have to redo your \
work. Everyone on the platform can read it, so file the finding and the \
reasoning behind it — a link and a distilled takeaway, never a pasted payload. \
Group related notes in a directory and give each a dated or subject path; keep \
your own working files (seen lists, checkpoints) in a directory named after you, \
one record per line, and pass that directory to check_lines and list_files so \
another component's notes never answer for yours. Notes are appended to, never \
replaced: append_file creates a note or adds to it.\
"""


def get_shared_notes_tools() -> list[Toolkit]:
    """The shared notebook for built components: read, append, list, search, check.

    No write, replace, move, or delete: those retire a colleague's work and stay
    with Agno, which carries the full toolkit.
    """
    return [
        notes.tools(
            name="shared_notes",
            include_tools=["read_file", "append_file", "list_files", "search_content", "check_lines"],
            instructions=SHARED_NOTES_INSTRUCTIONS,
            # Built agents have no other channel for usage guidance.
            add_instructions=True,
        )
    ]
