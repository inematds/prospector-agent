from __future__ import annotations
import json
import os
from dataclasses import dataclass, field


class SegredoAusente(Exception):
    pass


class Segredos:
    """Lê segredos do ambiente. Nunca loga o valor."""

    @staticmethod
    def exigir(nome: str) -> str:
        v = os.environ.get(nome, "").strip()
        if not v:
            raise SegredoAusente(f"Segredo ausente no ambiente: {nome}")
        return v

    @staticmethod
    def opcional(nome: str) -> str | None:
        v = os.environ.get(nome, "").strip()
        return v or None


@dataclass
class Config:
    nichos: list[str] = field(default_factory=list)
    meta_leads: int = 10
    dominio_publicacao: str | None = None
    from_email: str | None = None
    db_path: str = "prospector.db"


def carregar_config(path: str) -> Config:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return Config(
        nichos=d.get("nichos", []),
        meta_leads=d.get("meta_leads", 10),
        dominio_publicacao=d.get("dominio_publicacao"),
        from_email=d.get("from_email"),
        db_path=d.get("db_path", "prospector.db"),
    )
