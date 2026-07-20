from __future__ import annotations


def repair_latin1_mojibake(text: str) -> str:
    markers = ("Ã", "Â", "â", "ï¼", "ç", "å", "æ")
    if not any(marker in text for marker in markers):
        return text
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return text
    return repaired if repaired else text


class OpenAILLMClient:
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "",
        api_style: str = "responses",
        client=None,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.api_style = api_style
        self._client = client

    def complete(self, prompt: str) -> str:
        client = self._get_client()
        if self.api_style == "chat_completions":
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return repair_latin1_mojibake(self._extract_chat_completion_text(response)).strip()
        response = client.responses.create(model=self.model, input=prompt)
        output_text = getattr(response, "output_text", None)
        if output_text:
            return repair_latin1_mojibake(str(output_text)).strip()
        return repair_latin1_mojibake(self._extract_output_text(response)).strip()

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "openai is required for LLM_PROVIDER=openai. "
                    "Install project dependencies with `pip install -e .[dev]`."
                ) from exc
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def _extract_output_text(self, response) -> str:
        output_parts = getattr(response, "output", []) or []
        texts: list[str] = []
        for item in output_parts:
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    texts.append(str(text))
        return "\n".join(texts)

    def _extract_chat_completion_text(self, response) -> str:
        choices = getattr(response, "choices", []) or []
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", "") if message else ""
        return str(content or "")


class LLMClient:
    """Small LLM facade. The default stub keeps local development runnable."""

    def __init__(
        self,
        provider: str = "stub",
        model: str = "",
        api_key: str = "",
        base_url: str = "",
        api_style: str = "responses",
        client=None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.api_style = api_style
        self._client = client

    def complete(self, prompt: str) -> str:
        if self.provider == "stub":
            return self._stub_complete(prompt)
        if self.provider == "openai":
            return OpenAILLMClient(
                model=self.model or "gpt-5.1",
                api_key=self.api_key,
                base_url=self.base_url,
                api_style=self.api_style,
                client=self._client,
            ).complete(prompt)
        raise NotImplementedError(f"Unsupported LLM_PROVIDER: {self.provider}")

    def _stub_complete(self, prompt: str) -> str:
        prompt = prompt.strip()
        if not prompt:
            return "No input was provided."
        lines = [line.strip() for line in prompt.splitlines() if line.strip()]
        evidence_lines = [line for line in lines if line.startswith("[") or "Section:" in line]
        answer = [
            "This is a local PaperHermes draft generated from the provided paper context.",
            "It should be replaced by a configured LLM provider for production use.",
        ]
        if evidence_lines:
            answer.append("Key evidence considered:")
            answer.extend(f"- {line[:220]}" for line in evidence_lines[:5])
        return "\n".join(answer)
