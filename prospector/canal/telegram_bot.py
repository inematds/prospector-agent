from __future__ import annotations
import json
import time
import urllib.request
from prospector.canal.boundaries import enviar_telegram, API
from prospector.canal.mensagens import parse_prospectar


class TelegramBot:
    """Bot real (long-polling). Sem cobertura de teste. Liga o canal ao Orquestrador."""

    def __init__(self, token: str, chat_id: str, orquestrador, prospectar_fn):
        self.token = token
        self.chat_id = chat_id
        self.orq = orquestrador
        self.prospectar_fn = prospectar_fn
        self._offset = 0

    def notificar(self, texto: str) -> None:
        enviar_telegram(self.token, self.chat_id, texto)

    def tratar(self, texto: str) -> None:
        if texto.startswith("/prospectar"):
            nicho, cidade, auto = parse_prospectar(texto)
            self.prospectar_fn(nicho, cidade, auto)
        elif texto.startswith("/aprovar"):
            self.orq.aprovar(texto.split()[1])
        # NOTE: implementer adiciona o loop de getUpdates (polling) real aqui.

    def _get_updates(self, timeout: int = 30) -> list[dict]:
        url = API.format(token=self.token, metodo="getUpdates")
        data = json.dumps({"offset": self._offset, "timeout": timeout}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout + 10) as r:
            return json.loads(r.read()).get("result", [])

    def rodar(self, poll_timeout: int = 30) -> None:
        """Loop de long-polling real. Sem cobertura de teste (I/O de rede)."""
        while True:
            try:
                atualizacoes = self._get_updates(timeout=poll_timeout)
            except Exception:
                time.sleep(5)
                continue
            for upd in atualizacoes:
                self._offset = upd["update_id"] + 1
                msg = upd.get("message") or {}
                texto = msg.get("text", "")
                if texto:
                    self.tratar(texto)
