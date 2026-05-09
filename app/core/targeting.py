import ipaddress
import re
from dataclasses import dataclass
from enum import Enum

from app.core.config import Settings
from app.services.errors import TargetPolicyError

HOSTNAME_RE = re.compile(r"^(?=.{1,253}$)([A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
UNSAFE_TARGET_CHARS = re.compile(r"[\s;&|$`<>\"'{}()\[\]]")
PORT_EXPR_RE = re.compile(r"^\d{1,5}(?:-\d{1,5})?(?:,\d{1,5}(?:-\d{1,5})?)*$")


class TargetKind(str, Enum):
    ip = "ip"
    cidr = "cidr"
    hostname = "hostname"


@dataclass(frozen=True)
class ParsedTarget:
    value: str
    kind: TargetKind
    host_count: int = 1
    is_private: bool = False
    is_loopback: bool = False
    is_local_hostname: bool = False


def validate_target_syntax(raw_target: str, max_scan_hosts: int) -> ParsedTarget:
    target = raw_target.strip()
    if not target:
        raise ValueError("Target is required.")
    if "://" in target:
        raise ValueError("Use a hostname, IP address, or CIDR block, not a URL.")
    if UNSAFE_TARGET_CHARS.search(target):
        raise ValueError("Target contains unsupported characters.")
    if target.startswith("-"):
        raise ValueError("Target cannot start with a dash.")

    if "/" in target:
        try:
            network = ipaddress.ip_network(target, strict=False)
        except ValueError as exc:
            raise ValueError("CIDR target is not valid.") from exc
        if network.num_addresses > max_scan_hosts:
            raise ValueError(f"CIDR target is too large. Maximum hosts allowed: {max_scan_hosts}.")
        return ParsedTarget(
            value=str(network),
            kind=TargetKind.cidr,
            host_count=network.num_addresses,
            is_private=network.is_private,
            is_loopback=network.is_loopback,
        )

    try:
        address = ipaddress.ip_address(target)
        return ParsedTarget(
            value=str(address),
            kind=TargetKind.ip,
            is_private=address.is_private,
            is_loopback=address.is_loopback,
        )
    except ValueError:
        pass

    if target.lower() == "localhost":
        return ParsedTarget(
            value="localhost",
            kind=TargetKind.hostname,
            is_private=True,
            is_loopback=True,
            is_local_hostname=True,
        )

    if not HOSTNAME_RE.match(target):
        raise ValueError("Hostname target is not valid.")

    return ParsedTarget(value=target.lower(), kind=TargetKind.hostname)


def enforce_target_policy(raw_target: str, settings: Settings) -> ParsedTarget:
    parsed = validate_target_syntax(raw_target, settings.max_scan_hosts)
    local_names = {name.lower() for name in settings.local_hostnames}

    if parsed.kind == TargetKind.hostname and parsed.value in local_names:
        return ParsedTarget(
            value=parsed.value,
            kind=parsed.kind,
            host_count=parsed.host_count,
            is_private=True,
            is_loopback=parsed.value == "localhost",
            is_local_hostname=True,
        )

    if settings.allowed_target_mode == "any":
        return parsed

    if parsed.kind in {TargetKind.ip, TargetKind.cidr} and (parsed.is_private or parsed.is_loopback):
        return parsed

    raise TargetPolicyError(
        "Target is outside the default private scanning policy. "
        "Use localhost, a private IP/CIDR range, or set AEGIS_ALLOWED_TARGET_MODE=any only for authorized networks."
    )


def validate_ports_expression(value: str | None) -> str | None:
    if value is None:
        return None
    ports = value.strip()
    if not ports:
        return None
    if not PORT_EXPR_RE.match(ports):
        raise ValueError("Ports must be a comma-separated list of ports or ranges, for example 22,80,443 or 1-1024.")

    for part in ports.split(","):
        if "-" in part:
            start, end = [int(item) for item in part.split("-", 1)]
            if start > end:
                raise ValueError("Port ranges must be ascending.")
            if start < 1 or end > 65535:
                raise ValueError("Ports must be between 1 and 65535.")
        else:
            port = int(part)
            if port < 1 or port > 65535:
                raise ValueError("Ports must be between 1 and 65535.")
    return ports

