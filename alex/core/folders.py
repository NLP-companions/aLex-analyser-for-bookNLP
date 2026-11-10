"""Show a folder in the computer's file browser (Finder on macOS, Explorer on Windows, the desktop's file manager on Linux).

Used by the "Open" buttons beside the books folder, the source folders and the workspace folders, so you can see where to put
books. The API only ever asks for folders the analyser already knows (see api/workspaces.py), never a path a request names.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def launch(path: str):
    """Ask the system to show `path` (returns at once; the file browser opens on its own). Raises `OSError` if there is no way to.
    Tests replace this, so they never open a window."""
    if sys.platform == "win32":
        os.startfile(path)                                       # noqa: S606 - a folder the analyser knows, not a command
        return
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen([opener, path], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def open_folder(path) -> str:
    """Show a folder in the file browser -> its full path. A folder that isn't there, or a computer with no file browser to ask,
    is a `ValueError` that names the folder, so you can still find it by hand."""
    path = Path(path).expanduser().resolve()
    if not path.is_dir():
        raise ValueError(f"The folder {path} doesn't exist.")
    try:
        launch(str(path))
    except OSError:
        raise ValueError(f"This computer has no file browser aLex can ask to open folders. The folder is {path}") from None
    return str(path)
