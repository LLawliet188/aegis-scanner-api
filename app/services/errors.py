class ScanNotFoundError(Exception):
    """Raised when a requested scan ID is not in the store."""


class TargetPolicyError(Exception):
    """Raised when a target is syntactically valid but blocked by policy."""


class ScannerUnavailableError(Exception):
    """Raised when the configured scanner cannot run."""


class ScannerExecutionError(Exception):
    """Raised when a scanner process exits unsuccessfully."""

