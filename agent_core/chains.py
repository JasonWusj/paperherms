from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable


ANALYSIS_SYSTEM_PROMPTS = {
    "method": (
        "You are a paper method analysis expert. "
        "Analyze the methodology, model architecture, algorithm design, and technical approach. "
        "Output structured analysis in markdown."
    ),
    "experiments": (
        "You are a paper experiment analysis expert. "
        "Analyze experimental setup, datasets, metrics, baselines, ablation studies, and results. "
        "Output structured analysis in markdown."
    ),
    "novelty": (
        "You are a paper novelty analysis expert. "
        "Identify the main contributions, innovations, and differences from prior work. "
        "Output structured analysis in markdown."
    ),
    "limitations": (
        "You are a paper limitation analysis expert. "
        "Identify weaknesses, threats to validity, failure cases, and future work directions. "
        "Output structured analysis in markdown."
    ),
    "summary": (
        "You are a paper summarization expert. "
        "Produce a structured summary covering research problem, method, experiments, "
        "contributions, and limitations. Output in markdown."
    ),
}


def build_analysis_chain(llm: BaseChatModel, analysis_type: str) -> Runnable:
    system_prompt = ANALYSIS_SYSTEM_PROMPTS.get(analysis_type, ANALYSIS_SYSTEM_PROMPTS["summary"])
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        (
            "human",
            "Active skill guidance:\n{skills}\n\n"
            "If a relevant skill is present, follow its prompt template as the answer policy. "
            "Treat {{input}} as the current question plus retrieved paper context.\n\n"
            "Paper context:\n{context}\n\n"
            "User preferences:\n{memories}\n\n"
            "Please analyze.",
        ),
    ])
    return prompt | llm | StrOutputParser()


def build_plan_chain(llm: BaseChatModel) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are the PaperHermes task planner. "
            "Decide which analysis steps are needed for this task type. "
            "Return JSON with a 'steps' field containing a list of step names. "
            "Allowed steps: method, experiments, novelty, limitations, synthesis, reflection.",
        ),
        (
            "human",
            "Task type: {task_type}\n\n"
            "Available active skills:\n{skills}\n\n"
            "Active workflow lessons:\n{workflow_lessons}",
        ),
    ])
    return prompt | llm | StrOutputParser()


def build_learning_chain(llm: BaseChatModel) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are the PaperHermes learning reviewer. Extract reusable lessons after a task. "
            "Return JSON with memory_candidates, skill_candidates, and workflow_lessons. "
            "Keep candidates concise and grounded in the task result.",
        ),
        (
            "human",
            "Task type: {task_type}\n"
            "User input: {user_input}\n"
            "Reflection: {reflection}\n"
            "Answer:\n{answer}\n\n"
            "Agent outputs:\n{agent_outputs}\n\n"
            "Available skills:\n{skills}",
        ),
    ])
    return prompt | llm | StrOutputParser()


def build_synthesis_chain(llm: BaseChatModel) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a paper analysis synthesis expert. "
            "Combine the outputs from multiple analysis agents into a coherent, "
            "well-structured final answer. Output in markdown.",
        ),
        ("human", "Analysis outputs:\n{agent_outputs}\n\nPlease synthesize."),
    ])
    return prompt | llm | StrOutputParser()


def build_reflection_chain(llm: BaseChatModel) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are the PaperHermes reflection checker. "
            "Check if the answer is grounded in evidence. "
            "Return JSON with fields: status (checked/needs_evidence/weak), confidence (0-1), note.",
        ),
        ("human", "Answer:\n{answer}\n\nEvidence count: {evidence_count}"),
    ])
    return prompt | llm | StrOutputParser()


def build_qa_chain(llm: BaseChatModel) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a paper Q&A expert. Answer the user's question based on the paper content. "
            "Cite specific sections. Output in markdown.",
        ),
        (
            "human",
            "Question: {question}\n\n"
            "Active skill guidance:\n{skills}\n\n"
            "If a relevant skill is present, follow its prompt template as the answer policy. "
            "Treat {{input}} as the current question plus retrieved paper context.\n\n"
            "Paper context:\n{context}\n\n"
            "User preferences:\n{memories}",
        ),
    ])
    return prompt | llm | StrOutputParser()


def build_comparison_chain(llm: BaseChatModel) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a paper comparison expert. Compare multiple papers across dimensions: "
            "method, task, dataset, metrics, and contributions. Output a structured comparison table in markdown.",
        ),
        (
            "human",
            "Active skill guidance:\n{skills}\n\n"
            "Paper context:\n{context}\n\n"
            "Please produce a comparison.",
        ),
    ])
    return prompt | llm | StrOutputParser()


def build_related_work_chain(llm: BaseChatModel) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a Related Work writing expert. Generate a Related Work section draft "
            "based on the provided paper references. Write in academic style.",
        ),
        (
            "human",
            "Active skill guidance:\n{skills}\n\n"
            "Paper context:\n{context}\n\n"
            "Research topic: {topic}\n\n"
            "Please draft the Related Work.",
        ),
    ])
    return prompt | llm | StrOutputParser()
