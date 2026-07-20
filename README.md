# PaperHermes

PaperHermes is a research-paper assistant built around retrieval-augmented generation and a LangGraph multi-agent workflow. It parses papers, indexes sections and chunks, answers evidence-grounded questions, and records agent traces, memories, skills, evaluations, and improvement suggestions.

## Current capabilities

- FastAPI backend with PostgreSQL persistence and Qdrant vector search.
- PDF parsing, section extraction, metadata parsing, chunking, embeddings, and reranking.
- LangGraph workflow with intent routing, planning, specialist agents, synthesis, reflection, memory recall, and skill recall.
- OpenAI-compatible and stub LLM providers, so local development does not require a key.
- Agent traces, evaluation suites, replayable regression cases, improvement suggestions, review, and rollback.
- Human feedback rewards and an auditable LinUCB policy controller for economy, balanced, and deep retrieval arms.
- Next.js frontend for papers, chat, traces, memories, skills, and learning review.

## Quick start

1. Copy `.env.example` to `.env` and fill in local service or provider settings. Never commit `.env`.
2. Start PostgreSQL and Qdrant with `docker compose up postgres qdrant`.
3. Install the Python package with `pip install -e .` and start the API:

   ```bash
   uvicorn backend.main:app --reload
   ```

4. Start the frontend from `frontend/` with `npm install && npm run dev`.
5. Upload a PDF from the web UI, wait for indexing, and ask a question in the chat page.

The default `LLM_PROVIDER=stub` is safe for smoke tests. For real answers, configure an OpenAI-compatible endpoint using environment variables only.

### Policy learning

The default `POLICY_NAME=fixed` preserves the balanced baseline. Set `POLICY_NAME=linucb` to enable cold-start exploration and online LinUCB updates. Each task stores its context, action scores, propensity, selected arm, reward components, and policy version. Policy statistics and capped inverse-propensity replay are available from `/api/agent/policy/summary` and `/api/agent/policy/replay`.

## Data and model policy

Private `.env` files, database backups, uploaded PDFs, vector-store data, and model weights are ignored by Git. The repository contains only synthetic fixtures under `examples/`; use the download/import scripts to obtain local data.

## Roadmap

The next iteration will add structured citations, user feedback and reward events, Hybrid RAG policy arms, a LinUCB contextual-bandit controller, and a QLoRA SFT/DPO training pipeline. Each learned policy or model version will be evaluated against a fixed regression suite before activation.

## Security

If a key is ever exposed, revoke it and issue a replacement. Keep credentials in an untracked `.env` file or a deployment secret manager, not in source code, fixtures, screenshots, or logs.
