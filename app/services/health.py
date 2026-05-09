from app.utils.nmap_resolver import find_nmap_path


def is_nmap_available() -> bool:
    return find_nmap_path() is not None
