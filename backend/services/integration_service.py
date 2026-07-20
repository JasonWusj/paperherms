from __future__ import annotations

from typing import Any

import httpx

from backend.config import Settings, get_settings


class IntegrationNotificationService:
    def __init__(self, settings: Settings | None = None, http_client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self.http_client = http_client or httpx

    def notify_event(
        self,
        *,
        event_type: str,
        title: str,
        fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        text = self._format_text(event_type, title, fields or {})
        sent_channels: list[str] = []

        if self.settings.feishu_webhook_url:
            self._post_feishu(self.settings.feishu_webhook_url, text)
            sent_channels.append("feishu")

        if self.settings.wecom_webhook_url:
            self._post_wecom(self.settings.wecom_webhook_url, text)
            sent_channels.append("wecom")

        if not sent_channels:
            return {"status": "skipped", "reason": "notification webhook url not configured"}

        if sent_channels == ["feishu"]:
            return {"status": "sent", "channel": "feishu"}
        return {"status": "sent", "channels": sent_channels}

    def _post_feishu(self, webhook_url: str, text: str) -> None:
        response = self.http_client.post(
            webhook_url,
            json={
                "msg_type": "text",
                "content": {"text": text},
            },
            timeout=5,
        )
        response.raise_for_status()

    def _post_wecom(self, webhook_url: str, text: str) -> None:
        response = self.http_client.post(
            webhook_url,
            json={
                "msgtype": "text",
                "text": {"content": text},
            },
            timeout=5,
        )
        response.raise_for_status()

    def notify_evaluation_run_completed(self, run: dict[str, Any]) -> dict[str, Any]:
        summary = run.get("summary", {}) if isinstance(run.get("summary"), dict) else {}
        return self.notify_event(
            event_type="evaluation_run_completed",
            title="Evaluation run completed",
            fields={
                "run_id": run.get("id") or "",
                "suite": run.get("evaluation_suite") or "all",
                "trigger": run.get("trigger") or "",
                "tasks": summary.get("task_count", 0),
                "completion": summary.get("completion_rate", 0),
                "plan_completion": summary.get("plan_completion_rate", 0),
            },
        )

    def notify_improvement_suggestion_created(self, suggestion: dict[str, Any]) -> dict[str, Any]:
        return self.notify_event(
            event_type="improvement_suggestion_created",
            title="Improvement suggestion created",
            fields={
                "suggestion_id": suggestion.get("id") or "",
                "target": f"{suggestion.get('target_type') or ''}:{suggestion.get('target_id') or ''}",
                "type": suggestion.get("suggestion_type") or "",
                "reason": suggestion.get("reason") or "",
            },
        )

    def _format_text(self, event_type: str, title: str, fields: dict[str, Any]) -> str:
        lines = [f"PaperHermes: {title}", f"event: {event_type}"]
        lines.extend(f"{key}: {value}" for key, value in fields.items())
        return "\n".join(lines)
