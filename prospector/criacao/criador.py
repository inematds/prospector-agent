from __future__ import annotations
import os
from typing import Callable
from prospector.modelos import Lead, Estado
from prospector.criacao.capa import montar_capa
from prospector import maquina_estados as me
from prospector.estado import db


class Criador:
    def __init__(self, gerar_index: Callable[[Lead, str], None], base_dir: str = "sites"):
        self._gerar = gerar_index
        self._base = base_dir

    def redesenhar(self, lead: Lead, conn) -> str:
        dest = os.path.join(self._base, lead.slug)
        os.makedirs(dest, exist_ok=True)
        self._gerar(lead, dest)
        idx = os.path.join(dest, "index.html")
        if not os.path.exists(idx) or os.path.getsize(idx) == 0:
            raise RuntimeError(f"gerar_index não produziu index.html em {dest}")
        with open(os.path.join(dest, "proposta.html"), "w", encoding="utf-8") as f:
            f.write(montar_capa(lead))
        novo = me.avancar(Estado(lead.status), Estado.REDESENHADO)
        lead.status = novo.value
        db.atualizar_status(conn, lead.slug, novo.value)
        return dest
