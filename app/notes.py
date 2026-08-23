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


def read_shared_note(path: str) -> str:
    """Read one note from the platform's shared notebook.

    Use this to check what the team already knows before answering or filing.

    :param path: Note path, e.g. "decisions/vector-store.md". Get exact paths
        from list_shared_notes or search_shared_notes.
    :return: The note's contents, or a message saying it does not exist.
    """
    content = notes.read(path)
    if content is None:
        return f"No shared note at '{path}'. Use list_shared_notes to see what exists."
    return content


def write_shared_note(path: str, content: str) -> str:
    """Create a new note in the platform's shared notebook.

    Everyone on this platform can read what you write here, so file the finding
    and its reasoning, not raw payloads. This refuses to replace a note that
    already exists — use append_shared_note to add to one.

    :param path: Note path to create, e.g. "briefs/2026-08-23.md". Group related
        notes in a directory.
    :param content: The note body, in Markdown.
    :return: Confirmation, or an explanation if the path is taken.
    """
    try:
        meta = notes.write(path, content, overwrite=False)
    except Exception as exc:
        return (
            f"Could not create '{path}': {exc}. If it already exists, "
            "use append_shared_note to add to it instead of replacing it."
        )
    return f"Filed shared note '{meta.path}'."


def append_shared_note(path: str, content: str) -> str:
    """Add to a note in the platform's shared notebook, creating it if needed.

    The safe way to contribute to a note the team is already keeping: nothing
    that is there is lost.

    :param path: Note path to append to, e.g. "decisions/vector-store.md".
    :param content: Text to add at the end, in Markdown.
    :return: Confirmation.
    """
    try:
        meta = notes.append(path, content)
    except Exception as exc:
        return f"Could not append to '{path}': {exc}"
    return f"Appended to shared note '{meta.path}'."


def list_shared_notes(directory: str = "") -> str:
    """List the notes in the platform's shared notebook.

    :param directory: Limit to one directory, e.g. "briefs". Omit for everything.
    :return: One path per line, or a message when the directory is empty.
    """
    metas = notes.list(directory)
    if not metas:
        where = f" under '{directory}'" if directory else ""
        return f"No shared notes{where} yet."
    return "\n".join(meta.path for meta in metas)


def search_shared_notes(query: str, limit: int = 10) -> str:
    """Search the platform's shared notebook by content.

    :param query: Text to look for.
    :param limit: Most matches to return (default 10).
    :return: Matching paths with the matched text, or a message when nothing matches.
    """
    matches = notes.search(query, limit=limit)
    if not matches:
        return f"No shared note matches '{query}'."
    return "\n".join(f"{m.path}:{m.line}  {m.snippet.strip()}" for m in matches)


SHARED_NOTES_INSTRUCTIONS = """\
The shared notebook is how this platform remembers things across people and \
components. Read it before you answer a question about what the team has \
decided, and file what you learn so the next reader does not have to redo your \
work. Everyone on the platform can read it, so file the finding and the \
reasoning behind it — a link and a distilled takeaway, never a pasted payload. \
Group related notes in a directory and give each a dated or subject path. \
write_shared_note only creates; when a note already exists, append to it.\
"""


def get_shared_notes_tools() -> list[Toolkit]:
    """The scoped shared-notebook surface offered to built components.

    Create, append, read, list, search. No replace and no delete: those retire
    something a colleague wrote, and on a notebook everyone shares that decision
    belongs to Agno, which carries the full toolkit.
    """
    return [
        Toolkit(
            name="shared_notes",
            tools=[
                read_shared_note,
                write_shared_note,
                append_shared_note,
                list_shared_notes,
                search_shared_notes,
            ],
            instructions=SHARED_NOTES_INSTRUCTIONS,
            # Built agents have no other channel for usage guidance.
            add_instructions=True,
        )
    ]
