"""Translate problems + PageSpeed into rough monthly $ loss estimates.

All constants are deliberately rough industry-benchmark estimates. They are
documented inline so the rationale travels with the number. Output is always a
range (low, high), never a single figure.

Sources (rough industry benchmarks, not formal citations):
- Restaurant avg ticket ~$45 (US casual dining, 2024 NRA-ish range)
- Dental new-patient LTV ~$800 (DentalIntel/Patterson benchmarks)
- Realtor commission ~$8,000/deal (US median ~$400k home @ ~2% side)
- F&B online order avg ~$25 (DoorDash 2024 disclosures)
- Mobile bounce on 4s+ LCP ~+30% (Google web.dev / SOASTA)
"""
from __future__ import annotations

from typing import Any

from tools.audit._models import DollarImpact, DollarImpactItem, Problem

# Per-vertical: (low_loss_per_mo, high_loss_per_mo) baseline if a critical
# conversion-blocker is present. Tuned to feel believable to a small US SMB.
_BASELINE: dict[str, tuple[int, int]] = {
    # restaurant: 150 visitors/wk * 4 = 600/mo. Even 5–10 lost reservations
    # * $45 ticket * party-of-3 = $675–$1,350/mo per critical issue.
    "restaurant": (600, 1400),
    # dental: 1 lost new patient ($800 LTV) per critical issue per month is
    # conservative; 2 = $1,600. Range covers practice size variability.
    "dental": (800, 2400),
    # realtor: 1 missed lead per quarter that would have closed = $8k/3 ≈
    # $2,700/mo; range widens with deal size variance.
    "realtor": (1500, 4000),
    # fnb: ~$25 avg ticket, 20–40 lost online orders/mo per critical issue.
    "fnb": (500, 1200),
}

# Severity multipliers applied to the vertical baseline.
_SEV_MULT: dict[str, float] = {
    "critical": 1.0,
    "high": 0.5,
    "medium": 0.2,
    "low": 0.1,
}

# Codes that don't directly block conversion (omit from $ math).
_SKIP_CODES = {"no_schema_org", "no_h1", "dated_design_signals", "no_social_proof"}


def _baseline(vertical: str) -> tuple[int, int]:
    return _BASELINE.get(vertical, (300, 800))


def _problem_to_item(p: Problem, vertical: str) -> DollarImpactItem | None:
    if p.code in _SKIP_CODES:
        return None
    low, high = _baseline(vertical)
    mult = _SEV_MULT.get(p.severity, 0.2)
    return DollarImpactItem(
        code=p.code,
        low=int(round(low * mult)),
        high=int(round(high * mult)),
        rationale=(
            f"{vertical} baseline ${low}-${high}/mo * {p.severity} weight {mult} "
            f"for {p.code}."
        ),
    )


def _slow_load_item(vertical: str, lcp_ms: int) -> DollarImpactItem:
    low, high = _baseline(vertical)
    # ~30% extra bounce on slow LCP per Google web.dev guidance.
    mult = 0.3
    return DollarImpactItem(
        code="slow_load",
        low=int(round(low * mult)),
        high=int(round(high * mult)),
        rationale=(
            f"LCP {lcp_ms}ms > 4000ms; ~30% mobile bounce uplift on {vertical} "
            f"baseline ${low}-${high}/mo."
        ),
    )


def estimate_dollar_impact(
    problems: list[Problem],
    pagespeed: dict[str, Any] | None,
    vertical: str,
) -> DollarImpact:
    """Aggregate per-problem $ ranges + PageSpeed slow-load penalty."""
    breakdown: list[DollarImpactItem] = []
    for p in problems:
        item = _problem_to_item(p, vertical)
        if item is not None:
            breakdown.append(item)

    if pagespeed and not pagespeed.get("error"):
        lcp = pagespeed.get("lcp_ms")
        if isinstance(lcp, int) and lcp > 4000:
            breakdown.append(_slow_load_item(vertical, lcp))

    total_low = sum(it.low for it in breakdown)
    total_high = sum(it.high for it in breakdown)
    return DollarImpact(
        monthly_loss_low=total_low,
        monthly_loss_high=total_high,
        breakdown=breakdown,
    )
