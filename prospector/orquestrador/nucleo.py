from __future__ import annotations
from typing import Callable
from prospector.modelos import Lead, Estado
from prospector import maquina_estados as me
from prospector.estado import db
from prospector.canal.mensagens import msg_pedir_aprovacao, msg_enviado


def precisa_aprovacao(lead: Lead) -> bool:
    return not lead.sem_portao


class Orquestrador:
    def __init__(self, criador, publicador, mailer, notificar: Callable[[str], None], conn):
        self._criador = criador
        self._publicador = publicador
        self._mailer = mailer
        self._notificar = notificar
        self._conn = conn

    def processar(self, lead: Lead) -> None:
        dest = self._criador.redesenhar(lead, self._conn)      # -> redesenhado
        self._publicador.publicar(lead, self._conn, dest)      # -> publicado (+ urlNova)
        if precisa_aprovacao(lead):
            novo = me.avancar(Estado(lead.status), Estado.AGUARDANDO_APROVACAO)
            lead.status = novo.value
            db.atualizar_status(self._conn, lead.slug, novo.value)
            self._notificar(msg_pedir_aprovacao(lead))
        else:
            self._mailer.enviar(lead, self._conn)              # -> enviado
            self._notificar(msg_enviado(lead))

    def aprovar(self, slug: str) -> None:
        lead = db.ler_lead(self._conn, slug)
        if lead is None:
            raise ValueError(f"lead '{slug}' não encontrado")
        self._mailer.enviar(lead, self._conn)                  # aguardando_aprovacao -> enviado
        self._notificar(msg_enviado(lead))
