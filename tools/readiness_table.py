"""Generate readiness checklist markdown table."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

CHECKLIST_ITEMS = [
    "Cohort signals",
    "OOF stacking",
    "Calibration + band",
    "Microstructure overlays",
    "BMA/bandit",
    "Purged/embargoed WF-CV",
    "Risk controls",
    "Instrumentation/logging",
    "Logs v2 + snapshots",
]


def write_readiness_table(
    readiness: Dict[str, Tuple[str, str]],
    output_path: str | Path = "readiness_table.md",
) -> None:
    """Create the readiness checklist table from provided scores and reasons."""
    lines = [
        "| Checklist item | Score | One-sentence reason |",
        "| --- | --- | --- |",
    ]
    for item in CHECKLIST_ITEMS:
        score, reason = readiness.get(item, ("n/a", "No update provided."))
        lines.append(f"| {item} | {score} | {reason} |")
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    # Example usage; replace with real scores.
    example = {item: ("?", "TBD") for item in CHECKLIST_ITEMS}
    write_readiness_table(example)


if __name__ == "__main__":
    main()
