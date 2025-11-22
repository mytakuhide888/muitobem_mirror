from __future__ import annotations
from typing import Dict, Any
from django.utils import timezone

from social.models import DMMessage, Platform, WebhookEvent

def ingest_instagram_messaging(payload: Dict[str, Any]) -> int:
    """
    Instagram Webhook (object=instagram, entry[].messaging[]) を保存する。
    - 冪等化キー: message.mid
    - user_id: 相手側のID（is_echo True=こちら発信→recipient.id、False=相手発信→sender.id）
    戻り値: 新規作成件数
    """
    created = 0
    if not isinstance(payload, dict) or payload.get("object") != "instagram":
        return 0

    entries = payload.get("entry", []) or []
    for entry in entries:
        msgs = entry.get("messaging", []) or []
        for msg in msgs:
            m = (msg.get("message") or {})
            mid = m.get("mid")
            if not mid:
                continue
            # 冪等チェック（raw_json JSONField を前提に mid で照合）
            if DMMessage.objects.filter(raw_json__message__mid=mid).exists():
                continue

            is_echo = bool(m.get("is_echo"))
            sender_id = (msg.get("sender") or {}).get("id") or ""
            recipient_id = (msg.get("recipient") or {}).get("id") or ""
            # 相手側の user_id を保存
            user_id = recipient_id if is_echo else sender_id
            text = m.get("text", "")

            DMMessage.objects.create(
                platform=Platform.INSTAGRAM,
                user_id=user_id,
                text=text,
                sent_at=timezone.now(),
                raw_json=msg,
            )
            created += 1

    # 任意：WebhookEvent へ元payloadを1レコードだけ保存（容量対策で必要に応じて）
    try:
        WebhookEvent.objects.create(platform=Platform.INSTAGRAM, field="messages", payload=payload)
    except Exception:
        pass

    return created
