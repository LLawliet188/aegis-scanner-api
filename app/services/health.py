import os
import shutil
from pathlib import Path


def resolve_nmap_path(nmap_path: str) -> str | None:
    expanded_path = Path(os.path.expandvars(nmap_path)).expanduser()
    if expanded_path.is_file():
        return str(expanded_path)

    resolved_from_path = shutil.which(nmap_path)
    if resolved_from_path:
        return resolved_from_path

    if os.name != "nt":
        return None

    for env_name in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData"):
        base_path = os.environ.get(env_name)
        if not base_path:
            continue
        candidate = Path(base_path) / "Nmap" / "nmap.exe"
        if candidate.is_file():
            return str(candidate)

    return None


def is_nmap_available(nmap_path: str) -> bool:
    return resolve_nmap_path(nmap_path) is not None
