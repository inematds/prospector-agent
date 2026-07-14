from __future__ import annotations
from typing import Callable
from prospector.modelos import Lead, Estado
from prospector import maquina_estados as me
from prospector.estado import db


class Supressao:
    def __init__(self, emails=None):
        self._e = set(emails or [])

    def contem(self, email: str) -> bool:
        return email in self._e

    def adicionar(self, email: str) -> None:
        self._e.add(email)


def montar_corpo(lead: Lead) -> str:
    return (f"<p>Olá! Preparei uma nova versão do site de {lead.nome}.</p>"
            f'<p><a href="{lead.urlNova or "#"}">Ver a proposta ↗</a></p>'
            f'<hr><p style="font-size:12px;color:#888">Não quer mais receber? '
            f'Responda com "descadastrar" (opt-out).</p>')


class Mailer:
    def __init__(self, enviar_email: Callable[[str, str, str], str],
                 supressao: Supressao, from_email: str):
        self._enviar = enviar_email
        self._sup = supressao
        self._from = from_email

    def enviar(self, lead: Lead, conn) -> str | None:
        if self._sup.contem(lead.email or ""):
            return None
        novo = me.avancar(Estado(lead.status), Estado.ENVIADO)  # valida
        assunto = f"Uma ideia para o site de {lead.nome}"
        msg_id = self._enviar(lead.email, assunto, montar_corpo(lead))
        lead.status = novo.value
        lead.dataProposta = "enviado"
        db.salvar_lead(conn, lead)
        return msg_id
