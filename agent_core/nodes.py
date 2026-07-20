from __future__ import annotations

import json
import re
from typing import Any, Callable

from langchain_core.language_models.chat_models import BaseChatModel

from agent_core.chains import (
    build_analysis_chain,
    build_comparison_chain,
    build_learning_chain,
    build_plan_chain,
    build_qa_chain,
    build_reflection_chain,
    build_related_work_chain,
    build_synthesis_chain,
)
from agent_core.state import PaperAgentState


def classify_intent(text: str) -> str:
    """Rule-based intent classification (migrated from IntentRouterAgent.route)."""
    lowered = text.lower()
    if any(w in lowered for w in ["method", "approach", "algorithm", "模型", "方法"]):
        return "method"
    if any(w in lowered for w in ["experiment", "dataset", "metric", "实验", "数据集"]):
        return "experiments"
    if any(w in lowered for w in ["novel", "contribution", "创新", "贡献"]):
        return "novelty"
    if any(w in lowered for w in ["limitation", "weakness", "局限", "不足"]):
        return "limitations"
    if any(w in lowered for w in ["summary", "summarize", "总结"]):
        return "summary"
    if any(w in lowered for w in ["compare", "对比", "比较"]):
        return "compare"
    if any(w in lowered for w in ["related work", "相关工作"]):
        return "related_work"
    return "chat"


def _parse_plan_steps(text: str, task_type: str) -> list[str]:
    """Parse planner output, falling back to rules if LLM output is not valid JSON."""
    allowed = {"method", "experiments", "novelty", "limitations", "synthesis", "reflection"}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                payload = json.loads(match.group(0))
            except json.JSONDecodeError:
                payload = {}
        else:
            payload = {}
    steps = payload.get("steps") if isinstance(payload, dict) else None
    if isinstance(steps, list) and all(isinstance(s, str) and s in allowed for s in steps):
        return steps
    # Fallback rules (migrated from PlannerAgent._fallback_plan)
    if task_type == "summary":
        return ["method", "experiments", "novelty", "limitations", "synthesis"]
    if task_type == "deep_reading":
        return ["method", "experiments", "novelty", "limitations", "synthesis", "reflection"]
    if task_type in {"method", "experiments", "novelty", "limitations"}:
        return [task_type, "synthesis"]
    return ["synthesis"]


def _parse_reflection(text: str, evidence_count: int) -> dict[str, Any]:
    """Parse reflection output, falling back to rules."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                payload = json.loads(match.group(0))
            except json.JSONDecodeError:
                payload = {}
        else:
            payload = {}
    if isinstance(payload, dict) and "status" in payload:
        payload.setdefault("evidence_count", evidence_count)
        return payload
    # Fallback
    status = "needs_evidence" if evidence_count == 0 else "checked"
    confidence = 0.2 if evidence_count == 0 else 0.8
    return {"status": status, "confidence": confidence, "evidence_count": evidence_count}


def _extract_json_object(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {}
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    return payload if isinstance(payload, dict) else {}


def _fallback_learning(state: PaperAgentState) -> dict[str, Any]:
    reflection = state.get("reflection", {})
    answer = state.get("final_answer", "").strip()
    confidence = float(reflection.get("confidence", 0) or 0)
    if reflection.get("status") != "checked" or confidence <= 0.7 or len(answer) < 40:
        return {"memory_candidates": [], "skill_candidates": [], "workflow_lessons": []}

    task_type = state.get("task_type", "chat")
    user_input = state.get("user_input", "")
    memory_candidate = {
        "memory_type": "paper_analysis",
        "content": answer[:500],
        "confidence": confidence,
        "reason": "Reflection passed with paper evidence available.",
        "status": "draft",
    }
    skill_candidate = {
        "name": f"{task_type}_paper_workflow",
        "description": f"Reusable workflow learned from a {task_type} paper task.",
        "trigger_patterns": [task_type, *user_input.lower().split()[:3]],
        "steps": state.get("planned_steps", []) or [task_type],
        "prompt_template": "Use the learned PaperHermes workflow for: {input}",
        "confidence": min(confidence, 0.8),
        "status": "draft",
    }
    workflow_lesson = {
        "task_type": task_type,
        "lesson": "Use retrieved paper evidence, synthesize analysis, then run reflection before storing results.",
        "confidence": confidence,
    }
    return {
        "memory_candidates": [memory_candidate],
        "skill_candidates": [skill_candidate],
        "workflow_lessons": [workflow_lesson],
    }


def _parse_learning(text: str, state: PaperAgentState) -> dict[str, Any]:
    payload = _extract_json_object(text)
    keys = ("memory_candidates", "skill_candidates", "workflow_lessons")
    if all(isinstance(payload.get(key), list) for key in keys):
        return {key: payload.get(key, []) for key in keys}
    return _fallback_learning(state)


def format_chunks(chunks: list[dict]) -> str:
    return "\n".join(
        f"[{i+1}] Section: {c.get('section_title', 'N/A')}. {c.get('text', '')[:500]}"
        for i, c in enumerate(chunks)
        if c.get("text", "").strip()
    )


def format_memories(memories: list[dict]) -> str:
    return "\n".join(f"- {m.get('content', '')}" for m in memories) if memories else "None"


def format_workflow_lessons(lessons: list[dict]) -> str:
    if not lessons:
        return "None"
    lines = []
    for lesson in lessons:
        metadata = lesson.get("metadata_json", {}) or {}
        task_type = metadata.get("task_type") or lesson.get("task_type") or "general"
        lines.append(f"- ({task_type}) {lesson.get('content', lesson.get('lesson', ''))}")
    return "\n".join(lines)


def _model_or_dict_to_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return dict(item)
    return {
        key: value
        for key, value in getattr(item, "__dict__", {}).items()
        if not key.startswith("_")
    }


def format_skills(skills: list[dict]) -> str:
    if not skills:
        return "None"
    lines = []
    for skill in skills:
        metadata = skill.get("metadata_json", {}) or {}
        steps = metadata.get("steps", [])
        lines.append(
            f"- {skill.get('name', '')}: {skill.get('description', '')}. Steps: {', '.join(steps)}"
        )
    return "\n".join(lines)


def format_skill_policy(selected_skills: list[dict]) -> str:
    if not selected_skills:
        return "None"
    lines = []
    for skill in selected_skills:
        metadata = skill.get("metadata_json", {}) or {}
        steps = metadata.get("steps", [])
        template = str(skill.get("prompt_template", ""))[:1200]
        lines.append(
            "\n".join([
                f"- {skill.get('name', '')}",
                f"  reason: {skill.get('reason', '')}",
                f"  confidence: {skill.get('confidence', 0)}",
                f"  matched_patterns: {', '.join(skill.get('matched_patterns', [])) or 'None'}",
                f"  recommended_steps: {', '.join(steps) or 'None'}",
                f"  prompt_template: {template}",
            ])
        )
    return "\n".join(lines)


# ── Node factory functions ──────────────────────────────────────────────


def make_intent_router_node() -> Callable[[PaperAgentState], dict]:
    def node(state: PaperAgentState) -> dict:
        task_type = classify_intent(state["user_input"])
        return {"task_type": task_type}
    return node


def make_memory_recall_node(memory_service: Any) -> Callable[[PaperAgentState], dict]:
    def node(state: PaperAgentState) -> dict:
        try:
            memories = memory_service.search(state["user_id"], state["user_input"], limit=3)
            memory_dicts = [_model_or_dict_to_dict(memory) for memory in memories]
            workflow_lessons = [
                memory for memory in memory_dicts
                if memory.get("memory_type") == "workflow_lesson"
            ]
            regular_memories = [
                memory for memory in memory_dicts
                if memory.get("memory_type") != "workflow_lesson"
            ]
            trace_steps = []
            if workflow_lessons:
                trace_steps.append({
                    "agent_name": "MemoryManager",
                    "step_name": "recall_workflow_lessons",
                    "output": {
                        "lesson_count": len(workflow_lessons),
                        "lesson_ids": [lesson.get("id") for lesson in workflow_lessons if lesson.get("id")],
                        "task_type": state.get("task_type", "chat"),
                    },
                })
            return {
                "memories": regular_memories,
                "active_workflow_lessons": workflow_lessons,
                "trace_steps": trace_steps,
            }
        except Exception:
            return {"memories": [], "active_workflow_lessons": []}
    return node


def make_skill_recall_node(skill_service: Any) -> Callable[[PaperAgentState], dict]:
    def node(state: PaperAgentState) -> dict:
        if skill_service is None:
            return {"skills": [], "selected_skills": []}
        try:
            user_id = state.get("user_id", "default")
            task_type = state.get("task_type", "chat")
            user_input = state.get("user_input", "")
            if hasattr(skill_service, "select_for_task"):
                selected_skills = skill_service.select_for_task(user_id, task_type, user_input, limit=3)
                skills = selected_skills
            elif hasattr(skill_service, "search_for_task"):
                skills = [
                    _model_or_dict_to_dict(skill)
                    for skill in skill_service.search_for_task(user_id, task_type, user_input, limit=3)
                ]
                selected_skills = []
            else:
                return {"skills": [], "selected_skills": []}
            return {
                "skills": [_model_or_dict_to_dict(skill) for skill in skills],
                "selected_skills": [_model_or_dict_to_dict(skill) for skill in selected_skills],
                "trace_steps": [{
                    "agent_name": "SkillManager",
                    "step_name": "select_skills",
                    "output": {
                        "selected_count": len(selected_skills),
                        "selected_skills": [
                            {
                                "skill_id": skill.get("skill_id"),
                                "name": skill.get("name"),
                                "matched_patterns": skill.get("matched_patterns", []),
                                "confidence": skill.get("confidence", 0),
                                "reason": skill.get("reason", ""),
                            }
                            for skill in selected_skills
                        ],
                    },
                }],
            }
        except Exception:
            return {"skills": [], "selected_skills": []}
    return node


def make_retrieve_node(retriever: Any) -> Callable[[PaperAgentState], dict]:
    def node(state: PaperAgentState) -> dict:
        try:
            # If retriever has .invoke (LangChain retriever), use it
            if hasattr(retriever, "invoke"):
                docs = retriever.invoke(state["user_input"])
                chunks = []
                for doc in docs:
                    metadata = dict(doc.metadata)
                    chunks.append({
                        "id": metadata.get("id", metadata.get("chunk_id", "")),
                        "paper_id": metadata.get("paper_id", state.get("paper_id", "")),
                        "text": doc.page_content,
                        "section_title": metadata.get("section_title", ""),
                        "score": metadata.get("score", 0.0),
                        "page_start": metadata.get("page_start"),
                        "page_end": metadata.get("page_end"),
                    })
            # Otherwise use .search (custom interface returning RetrievedChunk)
            else:
                results = retriever.search(
                    state["user_input"],
                    paper_id=state.get("paper_id", ""),
                    limit=5,
                )
                chunks = [
                    {
                        "id": getattr(r, "id", ""),
                        "paper_id": getattr(r, "paper_id", ""),
                        "text": getattr(r, "text", ""),
                        "section_title": getattr(r, "section_title", ""),
                        "score": getattr(r, "score", 0.0),
                        "page_start": getattr(r, "page_start", None),
                        "page_end": getattr(r, "page_end", None),
                    }
                    for r in results
                ]
            return {
                "chunks": chunks,
                "trace_steps": [{
                    "agent_name": "RetrievalAgent",
                    "step_name": "retrieve_evidence",
                    "output": {"evidence_count": len(chunks)},
                    "retrieved_chunks": chunks,
                }],
            }
        except Exception:
            return {"chunks": []}
    return node


def make_plan_node(llm: BaseChatModel) -> Callable[[PaperAgentState], dict]:
    chain = build_plan_chain(llm)

    def node(state: PaperAgentState) -> dict:
        task_type = state.get("task_type", "chat")
        try:
            result = chain.invoke({
                "task_type": task_type,
                "skills": format_skill_policy(state.get("selected_skills", [])),
                "workflow_lessons": format_workflow_lessons(state.get("active_workflow_lessons", [])),
            })
            steps = _parse_plan_steps(result, task_type)
        except Exception:
            steps = _parse_plan_steps("", task_type)
        return {"planned_steps": steps}
    return node


def _make_analysis_node(llm: BaseChatModel, analysis_type: str, agent_name: str) -> Callable:
    chain = build_analysis_chain(llm, analysis_type)

    def node(state: PaperAgentState) -> dict:
        context = format_chunks(state.get("chunks", []))
        memories = format_memories(state.get("memories", []))
        skills = format_skill_policy(state.get("selected_skills", []))
        try:
            result = chain.invoke({"context": context, "memories": memories, "skills": skills})
        except Exception as exc:
            result = f"Analysis failed: {exc}"
        return {
            "agent_outputs": [{"agent_name": agent_name, "content": result}],
            "trace_steps": [{
                "agent_name": agent_name,
                "step_name": f"analyze_{analysis_type}",
                "output": result[:500],
            }],
        }
    return node


def make_method_node(llm: BaseChatModel) -> Callable:
    return _make_analysis_node(llm, "method", "MethodAgent")


def make_experiment_node(llm: BaseChatModel) -> Callable:
    return _make_analysis_node(llm, "experiments", "ExperimentReaderAgent")


def make_novelty_node(llm: BaseChatModel) -> Callable:
    return _make_analysis_node(llm, "novelty", "NoveltyAgent")


def make_limitation_node(llm: BaseChatModel) -> Callable:
    return _make_analysis_node(llm, "limitations", "LimitationAgent")


def make_comparison_node(llm: BaseChatModel) -> Callable:
    chain = build_comparison_chain(llm)

    def node(state: PaperAgentState) -> dict:
        context = format_chunks(state.get("chunks", []))
        skills = format_skill_policy(state.get("selected_skills", []))
        try:
            result = chain.invoke({"context": context, "skills": skills})
        except Exception as exc:
            result = f"Comparison failed: {exc}"
        return {
            "agent_outputs": [{"agent_name": "ComparisonAgent", "content": result}],
            "trace_steps": [{"agent_name": "ComparisonAgent", "step_name": "compare_papers", "output": result[:500]}],
        }
    return node


def make_related_work_node(llm: BaseChatModel) -> Callable:
    chain = build_related_work_chain(llm)

    def node(state: PaperAgentState) -> dict:
        context = format_chunks(state.get("chunks", []))
        topic = state.get("user_input", "")
        skills = format_skill_policy(state.get("selected_skills", []))
        try:
            result = chain.invoke({"context": context, "topic": topic, "skills": skills})
        except Exception as exc:
            result = f"Related work generation failed: {exc}"
        return {
            "agent_outputs": [{"agent_name": "RelatedWorkAgent", "content": result}],
            "trace_steps": [{"agent_name": "RelatedWorkAgent", "step_name": "generate_related_work", "output": result[:500]}],
        }
    return node


def make_qa_node(llm: BaseChatModel) -> Callable:
    chain = build_qa_chain(llm)

    def node(state: PaperAgentState) -> dict:
        context = format_chunks(state.get("chunks", []))
        memories = format_memories(state.get("memories", []))
        question = state.get("user_input", "")
        skills = format_skill_policy(state.get("selected_skills", []))
        try:
            result = chain.invoke({
                "question": question,
                "context": context,
                "memories": memories,
                "skills": skills,
            })
        except Exception as exc:
            result = f"QA failed: {exc}"
        return {
            "agent_outputs": [{"agent_name": "QAAgent", "content": result}],
            "final_answer": result,
            "trace_steps": [{"agent_name": "QAAgent", "step_name": "answer_question", "output": result[:500]}],
        }
    return node


def make_synthesis_node(llm: BaseChatModel) -> Callable:
    chain = build_synthesis_chain(llm)

    def node(state: PaperAgentState) -> dict:
        if state.get("final_answer"):
            return {"final_answer": state["final_answer"]}
        outputs = state.get("agent_outputs", [])
        if not outputs:
            return {"final_answer": "No analysis output was produced."}
        outputs_text = "\n\n".join(
            f"## {o.get('agent_name', 'Agent')}\n{o.get('content', '')}" for o in outputs
        )
        try:
            result = chain.invoke({"agent_outputs": outputs_text})
        except Exception as exc:
            result = f"Synthesis failed: {exc}"
        return {"final_answer": result, "citations": state.get("chunks", [])}
    return node


def make_reflection_node(llm: BaseChatModel) -> Callable:
    chain = build_reflection_chain(llm)

    def node(state: PaperAgentState) -> dict:
        answer = state.get("final_answer", "")
        evidence_count = len(state.get("chunks", []))
        try:
            result = chain.invoke({"answer": answer, "evidence_count": evidence_count})
            reflection = _parse_reflection(result, evidence_count)
        except Exception:
            reflection = _parse_reflection("", evidence_count)
        execution_feedback = _build_execution_feedback(state, reflection)
        return {
            "reflection": reflection,
            "execution_feedback": execution_feedback,
            "trace_steps": [{
                "agent_name": "ReflectionAgent",
                "step_name": "check_answer_grounding",
                "output": json.dumps(reflection),
            }, {
                "agent_name": "ReflectionAgent",
                "step_name": "evaluate_execution",
                "output": execution_feedback,
            }],
        }
    return node


def _build_execution_feedback(state: PaperAgentState, reflection: dict[str, Any]) -> dict[str, Any]:
    confidence = float(reflection.get("confidence", 0) or 0)
    reflection_status = str(reflection.get("status", ""))
    completed_agents = [
        output.get("agent_name", "Agent")
        for output in state.get("agent_outputs", [])
        if output.get("content")
    ]
    plan_status = "completed" if completed_agents and state.get("final_answer") else "incomplete"
    skill_status = "helpful" if reflection_status == "checked" and confidence >= 0.7 else "needs_review"
    workflow_lesson_status = "applied" if reflection_status == "checked" and confidence >= 0.7 else "needs_review"
    workflow_lesson_reason = (
        "workflow lesson was recalled before planning and answer reflection passed"
        if workflow_lesson_status == "applied"
        else "workflow lesson was recalled but answer reflection needs review"
    )
    return {
        "plan_feedback": {
            "status": plan_status,
            "planned_steps": state.get("planned_steps", []),
            "completed_agents": completed_agents,
            "evidence_count": len(state.get("chunks", [])),
        },
        "skill_feedback": [
            {
                "skill_id": skill.get("skill_id"),
                "name": skill.get("name"),
                "status": skill_status,
                "reason": "reflection passed with evidence" if skill_status == "helpful" else "reflection needs review",
                "reflection_confidence": confidence,
            }
            for skill in state.get("selected_skills", [])
            if skill.get("skill_id")
        ],
        "memory_feedback": [
            {
                "memory_id": memory.get("id"),
                "status": "used" if confidence >= 0.7 else "needs_review",
                "reason": "memory was recalled before answer reflection",
            }
            for memory in state.get("memories", [])
            if memory.get("id")
        ],
        "workflow_lesson_feedback": [
            {
                "lesson_id": lesson.get("id"),
                "status": workflow_lesson_status,
                "reason": workflow_lesson_reason,
                "reflection_confidence": confidence,
            }
            for lesson in state.get("active_workflow_lessons", [])
            if lesson.get("id")
        ],
    }


def make_learning_node(llm: BaseChatModel) -> Callable:
    chain = build_learning_chain(llm)

    def node(state: PaperAgentState) -> dict:
        outputs = state.get("agent_outputs", [])
        outputs_text = "\n\n".join(
            f"## {o.get('agent_name', 'Agent')}\n{o.get('content', '')}" for o in outputs
        )
        try:
            result = chain.invoke({
                "task_type": state.get("task_type", "chat"),
                "user_input": state.get("user_input", ""),
                "reflection": json.dumps({
                    "answer_reflection": state.get("reflection", {}),
                    "execution_feedback": state.get("execution_feedback", {}),
                }),
                "answer": state.get("final_answer", ""),
                "agent_outputs": outputs_text,
                "skills": format_skills(state.get("skills", [])),
            })
            learning = _parse_learning(result, state)
        except Exception:
            learning = _fallback_learning(state)
        skill_outcomes = _build_skill_outcomes(state)
        return {
            "learning": learning,
            "memory_candidates": learning.get("memory_candidates", []),
            "skill_candidates": learning.get("skill_candidates", []),
            "workflow_lessons": learning.get("workflow_lessons", []),
            "skill_outcomes": skill_outcomes,
            "trace_steps": [
                {
                    "agent_name": "LearningAgent",
                    "step_name": "extract_lessons",
                    "output": json.dumps(learning)[:500],
                },
                {
                    "agent_name": "SkillManager",
                    "step_name": "record_skill_outcomes",
                    "output": {"skill_outcomes": skill_outcomes},
                },
            ],
        }
    return node


def _build_skill_outcomes(state: PaperAgentState) -> list[dict[str, Any]]:
    reflection = state.get("reflection", {})
    confidence = float(reflection.get("confidence", 0) or 0)
    status = str(reflection.get("status", ""))
    if status == "checked" and confidence >= 0.7:
        outcome = "helpful"
    elif status:
        outcome = "needs_review"
    else:
        outcome = "unknown"
    return [
        {
            "skill_id": skill.get("skill_id"),
            "task_id": state.get("task_id"),
            "reflection_status": status,
            "reflection_confidence": confidence,
            "outcome": outcome,
        }
        for skill in state.get("selected_skills", [])
        if skill.get("skill_id")
    ]


def make_memory_write_node(memory_service: Any) -> Callable[[PaperAgentState], dict]:
    def node(state: PaperAgentState) -> dict:
        memory_candidates = state.get("memory_candidates", [])
        if memory_candidates:
            created = 0
            for candidate in memory_candidates:
                try:
                    from backend.schemas import MemoryCreate
                    metadata = {
                        "source": "learning",
                        "status": candidate.get("status", "draft"),
                        "confidence": candidate.get("confidence", 0.0),
                        "reason": candidate.get("reason", ""),
                        "source_task_id": state.get("task_id"),
                    }
                    memory_service.create(MemoryCreate(
                        user_id=state.get("user_id", "default"),
                        memory_type=candidate.get("memory_type", "paper_analysis"),
                        content=candidate.get("content", "")[:1000],
                        metadata=metadata,
                    ))
                    created += 1
                except Exception:
                    pass
            return {
                "trace_steps": [{
                    "agent_name": "MemoryManager",
                    "step_name": "write_learning_memories",
                    "output": f"Created {created} learning memories.",
                }]
            }

        reflection = state.get("reflection", {})
        answer = state.get("final_answer", "")
        user_id = state.get("user_id", "default")
        if (
            reflection.get("status") == "checked"
            and reflection.get("confidence", 0) > 0.7
            and len(answer.strip()) >= 40
        ):
            try:
                from backend.schemas import MemoryCreate
                memory_service.create(MemoryCreate(
                    user_id=user_id,
                    memory_type="paper_analysis",
                    content=answer[:500],
                    metadata={"source": "graph_reflection"},
                ))
            except Exception:
                pass
        return {}
    return node


def make_skill_write_node(skill_service: Any) -> Callable[[PaperAgentState], dict]:
    def node(state: PaperAgentState) -> dict:
        if skill_service is None or not hasattr(skill_service, "create_candidate"):
            return {}
        usage_updates = 0
        if hasattr(skill_service, "record_usage"):
            used_skill_ids = {
                str(outcome.get("skill_id"))
                for outcome in state.get("skill_outcomes", [])
                if outcome.get("skill_id")
            }
            for skill_id in used_skill_ids:
                try:
                    if skill_service.record_usage(skill_id):
                        usage_updates += 1
                except Exception:
                    pass
        created = 0
        for candidate in state.get("skill_candidates", []):
            try:
                skill_service.create_candidate(
                    state.get("user_id", "default"),
                    candidate,
                    source_task_id=state.get("task_id"),
                )
                created += 1
            except Exception:
                pass
        return {
            "trace_steps": [{
                "agent_name": "SkillManager",
                "step_name": "create_skill_candidates",
                "output": f"Recorded {usage_updates} skill uses. Created {created} skill candidates.",
            }]
        }
    return node
