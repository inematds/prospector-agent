from __future__ import annotations
from typing import Callable
from prospector.modelos import Lead, Estado
from prospector import maquina_estados as me
from prospector.estado import db


class Publicador:
    def __init__(self, publicar_arquivos: Callable[[str, str], None], base_url: str):
        self._pub = publicar_arquivos
        self._base_url = base_url.rstrip("/")

    def publicar(self, lead: Lead, conn, local_dir: str) -> str:
        novo = me.avancar(Estado(lead.status), Estado.PUBLICADO)  # valida transição
        self._pub(local_dir, lead.slug)
        url = f"{self._base_url}/{lead.slug}/"
        lead.urlNova = url
        lead.status = novo.value
        db.salvar_lead(conn, lead)
        return url
