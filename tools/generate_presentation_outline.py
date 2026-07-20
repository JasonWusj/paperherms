from __future__ import annotations


def generate_presentation_outline(summary: str) -> list[str]:
    return [
        "Background and problem",
        "Core method",
        "Experimental setup",
        "Main findings",
        "Limitations and discussion",
        f"Speaker note seed: {summary[:160]}",
    ]
