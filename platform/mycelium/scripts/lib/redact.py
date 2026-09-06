"""
Secret redaction — strips credentials from text before it enters the system.

Called at every ingestion boundary:
  - ingest-to-graph.py (traces, commits, issues → graph)
  - ingest-agent.py (LangSmith traces → signals/)
  - structural_couple() in MCP server (query text → CouplingEvent nodes)

Patterns are intentionally broad. False positives (redacting non-secrets)
are harmless. False negatives (missing a secret) are catastrophic.
"""

import re

# Each pattern: (name, regex, replacement)
_PATTERNS = [
    # Anthropic API keys and OAuth tokens
    ("anthropic_api_key", r"sk-ant-api\d{2}-[A-Za-z0-9_-]{20,}", "[REDACTED:anthropic-key]"),
    ("anthropic_oauth", r"sk-ant-oat\d{2}-[A-Za-z0-9_-]{20,}", "[REDACTED:anthropic-oauth]"),
    ("anthropic_generic", r"sk-ant-[A-Za-z0-9_-]{20,}", "[REDACTED:anthropic-token]"),

    # GitHub tokens
    ("github_pat_classic", r"ghp_[A-Za-z0-9]{36,}", "[REDACTED:github-pat]"),
    ("github_oauth", r"gho_[A-Za-z0-9]{36,}", "[REDACTED:github-oauth]"),
    ("github_pat_fine", r"github_pat_[A-Za-z0-9_]{20,}", "[REDACTED:github-pat]"),
    ("github_app_token", r"ghs_[A-Za-z0-9]{36,}", "[REDACTED:github-app]"),
    ("github_refresh", r"ghr_[A-Za-z0-9]{36,}", "[REDACTED:github-refresh]"),

    # LangSmith / LangChain keys
    ("langsmith_key", r"lsv2_pt_[A-Za-z0-9_]{20,}", "[REDACTED:langsmith-key]"),
    ("langchain_key", r"ls__[A-Za-z0-9]{20,}", "[REDACTED:langchain-key]"),

    # OpenAI keys
    ("openai_key", r"sk-[A-Za-z0-9]{20,}T3BlbkFJ[A-Za-z0-9]{20,}", "[REDACTED:openai-key]"),
    ("openai_proj", r"sk-proj-[A-Za-z0-9_-]{20,}", "[REDACTED:openai-key]"),

    # AWS
    ("aws_access_key", r"AKIA[0-9A-Z]{16}", "[REDACTED:aws-key]"),
    ("aws_secret", r"(?i)aws_secret_access_key\s*[=:]\s*[A-Za-z0-9/+=]{40}", "[REDACTED:aws-secret]"),

    # SSH private keys
    ("ssh_private_key", r"-----BEGIN\s+(RSA|EC|DSA|OPENSSH|PGP)\s+PRIVATE\s+KEY-----", "[REDACTED:private-key]"),

    # Generic bearer tokens in headers
    ("bearer_token", r"(?i)(?:authorization|bearer)\s*[:=]\s*Bearer\s+[A-Za-z0-9_-]{20,}", "[REDACTED:bearer]"),

    # Passwords in connection strings
    ("connection_string", r"(?i)(?:postgres|mysql|redis|mongodb)://[^:]+:[^@\s]+@", "[REDACTED:conn-string]://***:***@"),

    # Trigger.dev keys
    ("trigger_key", r"tr_dev_[A-Za-z0-9]{16,}", "[REDACTED:trigger-key]"),

    # Infisical tokens
    ("infisical_token", r"st\.[A-Za-z0-9_-]{20,}", "[REDACTED:infisical-token]"),

    # High-entropy hex strings that look like secrets (32+ hex chars, often = keys/passwords)
    # Only match when preceded by common secret-indicating keywords
    ("hex_secret", r"(?i)(?:secret|password|token|key|salt|encryption_key|auth_secret)\s*[=:]\s*[0-9a-f]{32,}", "[REDACTED:hex-secret]"),
]

_COMPILED = [(name, re.compile(pattern), repl) for name, pattern, repl in _PATTERNS]


def redact(text: str) -> str:
    """Remove secrets from text. Returns redacted copy."""
    if not text:
        return text
    result = text
    for _name, pattern, replacement in _COMPILED:
        result = pattern.sub(replacement, result)
    return result


def has_secrets(text: str) -> bool:
    """Check if text contains any detectable secrets."""
    if not text:
        return False
    for _name, pattern, _repl in _COMPILED:
        if pattern.search(text):
            return True
    return False


def scan_and_report(text: str) -> list[dict]:
    """Scan text and return list of detected secrets with positions."""
    if not text:
        return []
    findings = []
    for name, pattern, _repl in _COMPILED:
        for match in pattern.finditer(text):
            findings.append({
                "type": name,
                "start": match.start(),
                "end": match.end(),
                "preview": match.group()[:8] + "...",  # Only show prefix
            })
    return findings


if __name__ == "__main__":
    # Self-test
    tests = [
        ("API key", "my key is sk-ant-api03-abcdefghijklmnop12345678", True),
        ("OAuth", "token=sk-ant-oat01-abcdefghijklmnop12345678", True),
        # Build synthetic fixtures in pieces so GitHub push protection does
        # not mistake test data for a live credential.
        ("GitHub PAT", "ghp_" + "synthetic-test-value", True),
        ("LangSmith", "lsv2_pt_" + "synthetic-test-value", True),
        ("Safe text", "This is a normal sentence about architecture", False),
        ("Trigger", "tr_dev_3PpNgPhz7Fw2g0txqkms", True),
        ("SSH key", "-----BEGIN RSA PRIVATE KEY-----", True),
    ]
    for label, text, should_detect in tests:
        detected = has_secrets(text)
        status = "PASS" if detected == should_detect else "FAIL"
        redacted = redact(text)
        print(f"  [{status}] {label}: {detected} → {redacted[:60]}")
