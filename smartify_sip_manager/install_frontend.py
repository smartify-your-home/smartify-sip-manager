"""Install only Smartify-owned dashboard JavaScript into Home Assistant /local/.
No .storage modifications, no ownership of resources supplied by HACS.
"""
from pathlib import Path
import os
import shutil
import tempfile

SOURCE = Path("/app/frontend")
DESTINATION = Path("/homeassistant/www/smartify")
FILES = ("smartify-doorstation-card.js", "smartify-doorstation-popup.js",
         "smartify-sip-manager.js")

def install():
    if not SOURCE.is_dir() or not Path("/homeassistant").is_dir():
        print("Smartify frontend: HA config mount or bundled frontend missing; skipped.", flush=True)
        return
    if DESTINATION.is_symlink():
        raise RuntimeError("Smartify frontend: destination must not be a symlink")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        src = SOURCE / name
        dest = DESTINATION / name
        if not src.is_file() or src.is_symlink() or dest.is_symlink():
            raise RuntimeError("Smartify frontend: invalid source or target " + name)
        content = src.read_bytes()
        if dest.exists() and dest.read_bytes() == content:
            continue
        fd, tmp = tempfile.mkstemp(prefix=".smartify-", dir=DESTINATION)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
            os.chmod(tmp, 0o644)
            os.replace(tmp, dest)
            print("Smartify frontend installed: /local/smartify/" + name, flush=True)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

if __name__ == "__main__":
    install()
