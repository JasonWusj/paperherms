from __future__ import annotations


def generate_reading_notes(summary: str, method: str, experiments: str, limitations: str) -> str:
    return "\n\n".join(
        [
            "## Summary\n" + summary,
            "## Method\n" + method,
            "## Experiments\n" + experiments,
            "## Limitations\n" + limitations,
        ]
    )
