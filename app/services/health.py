import shutil


def is_nmap_available(nmap_path: str) -> bool:
    return shutil.which(nmap_path) is not None

