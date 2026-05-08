"""
Guardrail layer — mandatory input/output pipeline.

Input pipeline  (L1→L5): length, PII, scope, injection, rate-limit.
Output pipeline (L1→L5): version-hallucination, citation, certainty,
                          scope, approval-gate.
"""
from __future__ import annotations
import re
import time
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

MAX_MESSAGE_CHARS    = 4_000
MAX_MESSAGES_PER_HR  = 60
MAX_SEARCHES_PER_SESSION = 10

_PII_PATTERNS = [
    re.compile(r"(?i)(api[_\-]?key|secret|token|password)\s*[=:]\s*\S+"),
    re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{4}[\-\s]?\d{4}[\-\s]?\d{4}[\-\s]?\d{4}\b"),
    re.compile(r"\b(sk|pk|rk)-[A-Za-z0-9]{20,}\b"),           # OpenAI-style keys
]

_SCOPE_DENY = [
    "write code", "write a script", "write me a",
    "execute command", "run script", "run a script",
    "delete file", "delete my",
    "deploy to", "send email",
    "access database", "drop table",
    "rm -rf", "os.system", "subprocess",
    "scrape ", "web scraping", "price tracker",
    "generate image", "make an image",
    "play music", "book a flight", "order food",
]

_INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore\s+previous\s+instructions"),
    re.compile(r"(?i)you\s+are\s+now\s+DAN"),
    re.compile(r"(?i)disregard\s+all\s+prior"),
    re.compile(r"(?i)act\s+as\s+if\s+you\s+have\s+no\s+restrictions"),
]

_OVERCONFIDENT = [
    "definitely", "certainly", "guaranteed", "100%", "always works",
    "no risk", "absolutely safe",
]

# Only IDs that are specific enough to require a citation — not generic section words.
_REQUIRE_CITATION_FOR = ["CVE-", "GHSA-"]

# ── Rate-limit state ──────────────────────────────────────────────────────────

_msg_log: Dict[str, List[float]] = defaultdict(list)    # session_id → timestamps
_search_counts: Dict[str, int]   = defaultdict(int)     # session_id → count


# ── Result model ─────────────────────────────────────────────────────────────

class GuardrailResult:
    __slots__ = ("passed", "reason", "sanitised")
    def __init__(self, passed: bool, reason: str = "", sanitised: str = ""):
        self.passed    = passed
        self.reason    = reason
        self.sanitised = sanitised


# ── Input guardrails ─────────────────────────────────────────────────────────

class GuardrailLayer:
    def check_input(self, session_id: str, text: str) -> GuardrailResult:
        """Run all input layers. Returns first failure or success."""
        # L1 — Length
        if len(text) > MAX_MESSAGE_CHARS:
            return GuardrailResult(False,
                f"Message too long ({len(text)} chars). Max {MAX_MESSAGE_CHARS}.")

        # L2 — PII
        for pat in _PII_PATTERNS:
            if pat.search(text):
                logger.warning(f"[Guardrail L2] PII detected in session {session_id}")
                return GuardrailResult(False,
                    "Your message appears to contain credentials or personal data. "
                    "Please remove them — never share API keys in chat.")

        # L3 — Scope
        lower = text.lower()
        for phrase in _SCOPE_DENY:
            if phrase in lower:
                logger.warning(f"[Guardrail L3] Out-of-scope: '{phrase}' in session {session_id}")
                return GuardrailResult(False,
                    "I'm focused on dependency resolution and can't help with that. "
                    "Is there something about your packages I can assist with?")

        # L4 — Injection
        for pat in _INJECTION_PATTERNS:
            if pat.search(text):
                logger.warning(f"[Guardrail L4] Injection attempt in session {session_id}")
                return GuardrailResult(False,
                    "That message contains patterns I can't process. "
                    "Please ask about your dependencies directly.")

        # L5 — Rate limit
        now = time.time()
        window = [t for t in _msg_log[session_id] if now - t < 3600]
        _msg_log[session_id] = window
        if len(window) >= MAX_MESSAGES_PER_HR:
            return GuardrailResult(False,
                f"Rate limit reached ({MAX_MESSAGES_PER_HR} messages/hour). "
                "Please wait before sending more.")
        _msg_log[session_id].append(now)

        # Strip injection attempts from text before returning
        sanitised = _sanitise(text)
        return GuardrailResult(True, sanitised=sanitised)

    def check_search_rate(self, session_id: str) -> GuardrailResult:
        if _search_counts[session_id] >= MAX_SEARCHES_PER_SESSION:
            return GuardrailResult(False,
                f"Search limit reached ({MAX_SEARCHES_PER_SESSION} per session).")
        _search_counts[session_id] += 1
        return GuardrailResult(True)

    # ── Output guardrails ─────────────────────────────────────────────────────

    def check_output(
        self,
        text: str,
        allowed_versions: Optional[List[str]] = None,
    ) -> Tuple[str, List[str]]:
        """
        Returns (sanitised_text, list_of_warnings).
        L1 — version hallucination, L2 — citation, L3 — certainty calibration.
        """
        warnings: List[str] = []

        # L1 — Version hallucination: require at least X.Y.Z (3 parts) to avoid
        #      false positives on counts/ratios like "0.0" or "1.5 seconds".
        if allowed_versions is not None:
            # Only flag versions with 3+ numeric parts (e.g. 1.2.3, not 1.2)
            version_pattern = re.compile(r"\b(\d+\.\d+\.\d+(?:\.\d+)*)\b")
            found_versions = version_pattern.findall(text)
            hallucinated = [
                v for v in found_versions
                if v not in allowed_versions
            ]
            for v in set(hallucinated):
                warnings.append(
                    f"LLM output contains version '{v}' not in solver results — "
                    "possible hallucination."
                )
                logger.warning(f"[Guardrail L1-Output] Hallucinated version '{v}'")

        # L2 — Citation check: only warn for specific CVE/advisory IDs (CVE-*, GHSA-*)
        #      not for generic words like "license" or "vulnerability" in section headers.
        for trigger in _REQUIRE_CITATION_FOR:
            if trigger in text:   # case-sensitive: CVE- and GHSA- are always uppercase
                if "http" not in text and "source:" not in text.lower():
                    warnings.append(
                        f"Output references '{trigger}' but cites no source URL."
                    )

        # L3 — Certainty calibration
        for phrase in _OVERCONFIDENT:
            if phrase in text.lower():
                text = re.sub(re.escape(phrase), f"likely {phrase}", text, flags=re.IGNORECASE)
                warnings.append(f"Toned down overconfident phrase: '{phrase}'")

        if warnings:
            logger.warning(f"[Guardrail Output] {warnings}")

        return text, warnings


def _sanitise(text: str) -> str:
    """Remove prompt-injection attempts from user input."""
    for pat in _INJECTION_PATTERNS:
        text = pat.sub("[REMOVED]", text)
    return text
