from __future__ import annotations


REQUIRED_SUMMARY_TERMS = ("method", "experiment", "contribution", "limitation")


def summary_completeness(summary: str) -> float:
    lowered = summary.lower()
    covered = sum(1 for term in REQUIRED_SUMMARY_TERMS if term in lowered)
    return covered / len(REQUIRED_SUMMARY_TERMS)
