from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings
from app.core.targeting import enforce_target_policy
from app.models.scan import ScanOptions, ScanRequest
from app.services.errors import TargetPolicyError
from app.services.health import resolve_nmap_path
from app.services.nmap_runner import NmapScanner
from app.utils.nmap_parser import parse_nmap_xml


def test_private_policy_allows_localhost_and_blocks_public_hostname():
    settings = Settings(scan_engine="mock", allowed_target_mode="private")
    assert enforce_target_policy("127.0.0.1", settings).is_loopback is True

    try:
        enforce_target_policy("scanme.nmap.org", settings)
    except TargetPolicyError:
        pass
    else:
        raise AssertionError("Expected public hostname to be blocked by default policy.")


def test_nmap_command_uses_safe_defaults_when_privileged_options_disabled():
    settings = Settings(scan_engine="nmap", enable_os_detection=False, enable_vuln_scripts=False)
    scanner = NmapScanner(settings=settings)
    request = ScanRequest(
        target="127.0.0.1",
        options=ScanOptions(top_ports=10, os_detection=True, vuln_scripts=True),
    )

    command = scanner._build_command(request, Path("scan.xml"))

    assert "-sV" in command
    assert "-O" not in command
    assert "--script" not in command
    assert command[-1] == "127.0.0.1"


def test_nmap_path_resolver_accepts_explicit_executable(tmp_path):
    executable = tmp_path / "nmap.exe"
    executable.write_text("", encoding="utf-8")

    assert resolve_nmap_path(str(executable)) == str(executable)


def test_nmap_xml_parser_creates_structured_findings():
    xml = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <status state="up" />
    <address addr="127.0.0.1" addrtype="ipv4" />
    <ports>
      <port protocol="tcp" portid="23">
        <state state="open" />
        <service name="telnet" />
      </port>
      <port protocol="tcp" portid="8000">
        <state state="open" />
        <service name="http" product="Uvicorn" />
        <script id="http-title" output="Aegis API" />
      </port>
    </ports>
  </host>
</nmaprun>
"""
    now = datetime.now(UTC)
    result = parse_nmap_xml(
        scan_id="scan-1",
        target="127.0.0.1",
        xml_text=xml,
        started_at=now,
        finished_at=now,
        command_profile="test",
    )

    assert result.summary["hosts_up"] == 1
    assert result.summary["open_ports"] == 2
    assert {vulnerability.id for vulnerability in result.vulnerabilities} == {
        "AEGIS-TELNET-EXPOSED",
        "NMAP-SCRIPT-HTTP-TITLE",
    }
