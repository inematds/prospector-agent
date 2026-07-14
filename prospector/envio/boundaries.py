from __future__ import annotations
import json
import urllib.request


def enviar_resend(to: str, assunto: str, html: str, from_email: str, api_key: str) -> str:
    payload = json.dumps({"from": from_email, "to": [to], "subject": assunto, "html": html}).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=payload, method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("id", "")
