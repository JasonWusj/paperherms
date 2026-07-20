from __future__ import annotations

from agent_core.state import AgentRunResult


def task_completion_rate(results: list[AgentRunResult]) -> float:
    if not results:
        return 0.0
    completed = sum(1 for result in results if result.final_output.strip())
    return completed / len(results)
