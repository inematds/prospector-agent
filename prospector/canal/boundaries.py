from __future__ import annotations
import json
import urllib.request

API = "https://api.telegram.org/bot{token}/{metodo}"


def enviar_telegram(token: str, chat_id: str, texto: str) -> None:
    url = API.format(token=token, metodo="sendMessage")
    data = json.dumps({"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30).read()
