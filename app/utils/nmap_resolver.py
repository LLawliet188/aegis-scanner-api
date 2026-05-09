import os
import shutil
from pathlib import Path

from dotenv import dotenv_values

NMAP_NOT_INSTALLED_MESSAGE = "Nmap not installed. Install Nmap or set AEGIS_NMAP_PATH."

WINDOWS_COMMON_NMAP_PATHS = (
    Path(r"C:\Program Files (x86)\Nmap\nmap.exe"),
    Path(r"C:\Program Files\Nmap\nmap.exe"),
)


def _valid_executable(path_value: str | Path) -> str | None:
    path = Path(os.path.expandvars(str(path_value))).expanduser()
    if path.is_file():
        return str(path)
    return None


def _read_env_value(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value

    dotenv_value = dotenv_values(".env").get(name)
    if isinstance(dotenv_value, str):
        return dotenv_value.strip()

    return ""


def find_nmap_path() -> str | None:
    """Return the first usable Nmap executable path without raising."""
    env_path = _read_env_value("AEGIS_NMAP_PATH")
    if env_path and env_path.lower() not in {"nmap", "nmap.exe"}:
        return _valid_executable(env_path)

    if os.name == "nt":
        for candidate in WINDOWS_COMMON_NMAP_PATHS:
            executable = _valid_executable(candidate)
            if executable:
                return executable

    path_executable = shutil.which("nmap")
    if path_executable:
        return path_executable

    return None


def get_nmap_path() -> str:
    """Return a usable Nmap executable path or fail with an operator-friendly error."""
    nmap_path = find_nmap_path()
    if not nmap_path:
        raise RuntimeError(NMAP_NOT_INSTALLED_MESSAGE)
    return nmap_path
