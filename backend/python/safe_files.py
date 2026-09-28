"""Case-insensitive FileResponse (Windows dev -> Linux hosting fix)."""
import os
from fastapi.responses import FileResponse as _FileResponse


def FileResponse(path, *args, **kwargs):
    if isinstance(path, (str, os.PathLike)) and not os.path.exists(path):
        folder, name = os.path.split(str(path))
        try:
            for f in os.listdir(folder):
                if f.lower() == name.lower():
                    path = os.path.join(folder, f)
                    break
        except OSError:
            pass
    return _FileResponse(path, *args, **kwargs)
