from __future__ import annotations

from typing import Any, List, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from tools.llm_client import LLMClient


class PaperHermesLLM(BaseChatModel):
    """LangChain-compatible wrapper around tools.llm_client.LLMClient."""

    provider: str = "stub"
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    api_style: str = "responses"

    @property
    def _llm_type(self) -> str:
        return "paperhermes"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        prompt = self._messages_to_prompt(messages)
        client = LLMClient(
            provider=self.provider,
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            api_style=self.api_style,
        )
        text = client.complete(prompt)
        message = AIMessage(content=text)
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        parts: list[str] = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                parts.append(f"[System] {msg.content}")
            elif isinstance(msg, HumanMessage):
                parts.append(msg.content)
            else:
                parts.append(str(msg.content))
        return "\n\n".join(parts)
