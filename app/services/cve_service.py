from app.models.scan import ScanResult


class CveEnrichmentService:
    """Placeholder boundary for later CVE intelligence providers.

    This keeps network calls out of the scanner path today while making it easy to add
    NVD, OSV, commercial feeds, or an internal enrichment cache later.
    """

    async def enrich(self, result: ScanResult) -> ScanResult:
        for vulnerability in result.vulnerabilities:
            vulnerability.cve_enrichment_status = "pending_provider_integration"
        return result

