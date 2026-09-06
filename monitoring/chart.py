"""The one required chart: corrected prevalence over time, with a threshold.

Instructor-provided. Renders a small self-contained SVG so the homework
needs no plotting dependency. The chart answers the dashboard's first
question ("is quality holding?") with the action attached: when the
corrected prevalence crosses the threshold line, pull the flagged traces,
do error analysis, and mint a new evaluation case.

Usage:
    from monitoring.chart import prevalence_chart
    svg = prevalence_chart(points, threshold=0.15, mode="unsupported_policy_claim")
    Path("monitoring/prevalence.svg").write_text(svg)

`points` is a list of dicts: {"label": "2026-W26", "corrected": 0.16,
"ci_low": 0.09, "ci_high": 0.24}.
"""

from __future__ import annotations

from typing import Any

_W, _H = 720, 360
_MARGIN = 56


def _x(i: int, n: int) -> float:
    span = _W - 2 * _MARGIN
    return _MARGIN + (span * i / max(n - 1, 1))


def _y(value: float, y_max: float) -> float:
    span = _H - 2 * _MARGIN
    return _H - _MARGIN - span * (value / y_max)


def prevalence_chart(
    points: list[dict[str, Any]], threshold: float, mode: str
) -> str:
    """Render the corrected-prevalence time series as an SVG string."""
    if not points:
        raise ValueError("no points to chart")
    y_max = max(
        [threshold] + [p["ci_high"] for p in points] + [p["corrected"] for p in points]
    ) * 1.25
    n = len(points)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_W}" height="{_H}" '
        f'viewBox="0 0 {_W} {_H}" font-family="sans-serif">',
        f'<rect width="{_W}" height="{_H}" fill="white"/>',
        f'<text x="{_MARGIN}" y="28" font-size="16" font-weight="bold">'
        f"{mode}: corrected prevalence over time</text>",
        # Axes.
        f'<line x1="{_MARGIN}" y1="{_H - _MARGIN}" x2="{_W - _MARGIN}" '
        f'y2="{_H - _MARGIN}" stroke="#444"/>',
        f'<line x1="{_MARGIN}" y1="{_MARGIN}" x2="{_MARGIN}" '
        f'y2="{_H - _MARGIN}" stroke="#444"/>',
        # Threshold line, the "so what": crossing it triggers error analysis.
        f'<line x1="{_MARGIN}" y1="{_y(threshold, y_max):.1f}" '
        f'x2="{_W - _MARGIN}" y2="{_y(threshold, y_max):.1f}" '
        f'stroke="#c0341f" stroke-dasharray="6,4"/>',
        f'<text x="{_W - _MARGIN + 4}" y="{_y(threshold, y_max) + 4:.1f}" '
        f'font-size="11" fill="#c0341f">threshold {threshold:.2f}</text>',
    ]
    # Confidence band as per-point whiskers.
    for i, p in enumerate(points):
        x = _x(i, n)
        parts.append(
            f'<line x1="{x:.1f}" y1="{_y(p["ci_low"], y_max):.1f}" '
            f'x2="{x:.1f}" y2="{_y(p["ci_high"], y_max):.1f}" '
            f'stroke="#8888dd" stroke-width="3" opacity="0.6"/>'
        )
    # The corrected-prevalence line and points.
    coords = [f"{_x(i, n):.1f},{_y(p['corrected'], y_max):.1f}" for i, p in enumerate(points)]
    parts.append(
        f'<polyline points="{" ".join(coords)}" fill="none" stroke="#2244aa" '
        f'stroke-width="2"/>'
    )
    for i, p in enumerate(points):
        x, y = _x(i, n), _y(p["corrected"], y_max)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#2244aa"/>')
        parts.append(
            f'<text x="{x:.1f}" y="{_H - _MARGIN + 18}" font-size="11" '
            f'text-anchor="middle">{p["label"]}</text>'
        )
    # Y-axis ticks at 0, half, and max.
    for value in (0.0, y_max / 2, y_max):
        parts.append(
            f'<text x="{_MARGIN - 8}" y="{_y(value, y_max) + 4:.1f}" font-size="11" '
            f'text-anchor="end">{value:.2f}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)
