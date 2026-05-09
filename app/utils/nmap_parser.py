import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

from app.models.scan import HostFinding, PortFinding, ScanResult, Vulnerability

RISKY_SERVICE_PORTS = {
    21: ("AEGIS-FTP-EXPOSED", "FTP service exposed", "medium", "FTP often transmits credentials without encryption."),
    23: ("AEGIS-TELNET-EXPOSED", "Telnet service exposed", "high", "Telnet is unencrypted and should not be exposed."),
    445: ("AEGIS-SMB-EXPOSED", "SMB service exposed", "medium", "SMB exposure should be restricted to trusted networks."),
    3389: ("AEGIS-RDP-EXPOSED", "RDP service exposed", "medium", "RDP exposure should be protected with MFA and network controls."),
    5900: ("AEGIS-VNC-EXPOSED", "VNC service exposed", "medium", "VNC exposure should be restricted and strongly authenticated."),
    6379: ("AEGIS-REDIS-EXPOSED", "Redis service exposed", "high", "Redis should not be exposed without strict network controls."),
    9200: ("AEGIS-ELASTICSEARCH-EXPOSED", "Elasticsearch service exposed", "high", "Elasticsearch exposure can leak sensitive data."),
    27017: ("AEGIS-MONGODB-EXPOSED", "MongoDB service exposed", "high", "MongoDB exposure can leak sensitive data."),
}


def parse_nmap_xml(
    scan_id: str,
    target: str,
    xml_text: str,
    started_at: datetime,
    finished_at: datetime,
    command_profile: str,
) -> ScanResult:
    python_nmap_data = _try_python_nmap_parse(xml_text)
    root = ET.fromstring(xml_text)
    hosts = [_parse_host(host_node) for host_node in root.findall("host")]
    vulnerabilities = _build_vulnerabilities(hosts)
    summary = _build_summary(hosts, vulnerabilities)

    if python_nmap_data and "scan" in python_nmap_data:
        summary["python_nmap_hosts"] = len(python_nmap_data.get("scan", {}))

    return ScanResult(
        scan_id=scan_id,
        target=target,
        started_at=started_at,
        finished_at=finished_at,
        command_profile=command_profile,
        hosts=hosts,
        vulnerabilities=vulnerabilities,
        summary=summary,
    )


def _try_python_nmap_parse(xml_text: str) -> dict[str, Any] | None:
    try:
        import nmap

        scanner = nmap.PortScanner()
        return scanner.analyse_nmap_xml_scan(nmap_xml_output=xml_text)
    except Exception:
        return None


def _parse_host(host_node: ET.Element) -> HostFinding:
    address_node = host_node.find("address")
    address = address_node.attrib.get("addr", "unknown") if address_node is not None else "unknown"
    hostname = None
    hostname_node = host_node.find("./hostnames/hostname")
    if hostname_node is not None:
        hostname = hostname_node.attrib.get("name")

    status_node = host_node.find("status")
    state = status_node.attrib.get("state", "unknown") if status_node is not None else "unknown"

    os_matches = [
        match.attrib.get("name", "")
        for match in host_node.findall("./os/osmatch")
        if match.attrib.get("name")
    ]

    ports = [_parse_port(port_node) for port_node in host_node.findall("./ports/port")]
    return HostFinding(address=address, hostname=hostname, state=state, os_matches=os_matches, ports=ports)


def _parse_port(port_node: ET.Element) -> PortFinding:
    state_node = port_node.find("state")
    service_node = port_node.find("service")
    scripts = {
        script.attrib.get("id", "script"): script.attrib.get("output", "")
        for script in port_node.findall("script")
        if script.attrib.get("output")
    }

    return PortFinding(
        port=int(port_node.attrib.get("portid", "0")),
        protocol=port_node.attrib.get("protocol", "tcp"),
        state=state_node.attrib.get("state", "unknown") if state_node is not None else "unknown",
        service=service_node.attrib.get("name") if service_node is not None else None,
        product=service_node.attrib.get("product") if service_node is not None else None,
        version=service_node.attrib.get("version") if service_node is not None else None,
        extra_info=service_node.attrib.get("extrainfo") if service_node is not None else None,
        scripts=scripts,
    )


def _build_vulnerabilities(hosts: list[HostFinding]) -> list[Vulnerability]:
    vulnerabilities: list[Vulnerability] = []
    for host in hosts:
        for port in host.ports:
            if port.state != "open":
                continue
            if port.port in RISKY_SERVICE_PORTS:
                vuln_id, title, severity, description = RISKY_SERVICE_PORTS[port.port]
                vulnerabilities.append(
                    Vulnerability(
                        id=vuln_id,
                        title=title,
                        severity=severity,
                        description=description,
                        host=host.address,
                        port=port.port,
                        service=port.service,
                        evidence=f"{port.port}/{port.protocol} open",
                    )
                )
            for script_id, output in port.scripts.items():
                vulnerabilities.append(
                    Vulnerability(
                        id=f"NMAP-SCRIPT-{script_id.upper()}",
                        title=f"Nmap script finding: {script_id}",
                        severity="medium",
                        description="Nmap vulnerability script returned output for this service.",
                        host=host.address,
                        port=port.port,
                        service=port.service,
                        evidence=output[:1000],
                        metadata={"script_id": script_id},
                    )
                )
    return vulnerabilities


def _build_summary(hosts: list[HostFinding], vulnerabilities: list[Vulnerability]) -> dict[str, int]:
    return {
        "hosts_total": len(hosts),
        "hosts_up": sum(1 for host in hosts if host.state == "up"),
        "open_ports": sum(1 for host in hosts for port in host.ports if port.state == "open"),
        "vulnerabilities": len(vulnerabilities),
        "critical": sum(1 for vuln in vulnerabilities if vuln.severity == "critical"),
        "high": sum(1 for vuln in vulnerabilities if vuln.severity == "high"),
        "medium": sum(1 for vuln in vulnerabilities if vuln.severity == "medium"),
        "low": sum(1 for vuln in vulnerabilities if vuln.severity == "low"),
        "info": sum(1 for vuln in vulnerabilities if vuln.severity == "info"),
    }

