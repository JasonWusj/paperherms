from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from agent_core.nodes import (
    make_comparison_node,
    make_experiment_node,
    make_intent_router_node,
    make_limitation_node,
    make_learning_node,
    make_memory_recall_node,
    make_memory_write_node,
    make_method_node,
    make_novelty_node,
    make_plan_node,
    make_qa_node,
    make_related_work_node,
    make_retrieve_node,
    make_skill_recall_node,
    make_skill_write_node,
    make_synthesis_node,
    make_reflection_node,
)
from agent_core.state import PaperAgentState

# Mapping from planned step name to graph node name
STEP_TO_NODE = {
    "method": "method_agent",
    "experiments": "experiment_agent",
    "novelty": "novelty_agent",
    "limitations": "limitation_agent",
    "synthesis": "synthesis",
    "reflection": "reflection",
}

# Mapping from task_type to the single analysis node it should route to
TASK_TO_NODE = {
    "method": ["method_agent"],
    "experiments": ["experiment_agent"],
    "novelty": ["novelty_agent"],
    "limitations": ["limitation_agent"],
    "compare": ["comparison_agent"],
    "related_work": ["related_work_agent"],
    "chat": ["qa_agent"],
}

ANALYSIS_NODES = {"method_agent", "experiment_agent", "novelty_agent", "limitation_agent"}


def route_by_plan(state: PaperAgentState) -> list[str]:
    """Conditional routing: decide which analysis nodes to execute."""
    task_type = state.get("task_type", "chat")

    # Special single-node tasks
    if task_type in TASK_TO_NODE:
        return TASK_TO_NODE[task_type]

    # Multi-step tasks: use planned_steps to determine nodes
    planned = state.get("planned_steps", [])
    targets = []
    for step in planned:
        node = STEP_TO_NODE.get(step)
        if node and node in ANALYSIS_NODES:
            targets.append(node)

    if not targets:
        return ["synthesis"]

    return targets


def build_paper_graph(
    llm: BaseChatModel,
    retriever: Any,
    memory_service: Any,
    trace_service: Any,
    skill_service: Any | None = None,
) -> Any:
    """Build and compile the LangGraph StateGraph for paper analysis."""
    graph = StateGraph(PaperAgentState)

    # Register nodes
    graph.add_node("intent_router", make_intent_router_node())
    graph.add_node("memory_recall", make_memory_recall_node(memory_service))
    graph.add_node("skill_recall", make_skill_recall_node(skill_service))
    graph.add_node("retrieve_chunks", make_retrieve_node(retriever))
    graph.add_node("plan", make_plan_node(llm))
    graph.add_node("qa_agent", make_qa_node(llm))
    graph.add_node("method_agent", make_method_node(llm))
    graph.add_node("experiment_agent", make_experiment_node(llm))
    graph.add_node("novelty_agent", make_novelty_node(llm))
    graph.add_node("limitation_agent", make_limitation_node(llm))
    graph.add_node("comparison_agent", make_comparison_node(llm))
    graph.add_node("related_work_agent", make_related_work_node(llm))
    graph.add_node("synthesis", make_synthesis_node(llm))
    graph.add_node("reflection", make_reflection_node(llm))
    graph.add_node("learning", make_learning_node(llm))
    graph.add_node("memory_write", make_memory_write_node(memory_service))
    graph.add_node("skill_write", make_skill_write_node(skill_service))

    # Main path edges
    graph.add_edge(START, "intent_router")
    graph.add_edge("intent_router", "memory_recall")
    graph.add_edge("memory_recall", "skill_recall")
    graph.add_edge("skill_recall", "retrieve_chunks")
    graph.add_edge("retrieve_chunks", "plan")

    # Conditional routing from plan to analysis nodes
    all_analysis_targets = list(ANALYSIS_NODES) + [
        "qa_agent", "comparison_agent", "related_work_agent", "synthesis"
    ]
    graph.add_conditional_edges(
        "plan",
        route_by_plan,
        {node: node for node in all_analysis_targets},
    )

    # All analysis nodes converge to synthesis
    for node in ANALYSIS_NODES | {"qa_agent", "comparison_agent", "related_work_agent"}:
        graph.add_edge(node, "synthesis")

    # Post-synthesis path
    graph.add_edge("synthesis", "reflection")
    graph.add_edge("reflection", "learning")
    graph.add_edge("learning", "memory_write")
    graph.add_edge("memory_write", "skill_write")
    graph.add_edge("skill_write", END)

    return graph.compile()
