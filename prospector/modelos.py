from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum


class Estado(str, Enum):
    DESCOBERTO = "descoberto"
    QUALIFICADO = "qualificado"
    REDESENHADO = "redesenhado"
    PUBLICADO = "publicado"
    AGUARDANDO_APROVACAO = "aguardando_aprovacao"
    ENVIADO = "enviado"
    RESPONDIDO = "respondido"
    FECHADO = "fechado"
    DESCARTADO = "descartado"
    ERRO = "erro"


# Schema do Store — compatível com o dashboard.html da referência.
CAMPOS = [
    "slug", "nome", "nicho", "cidade", "nota", "avaliacoes", "email",
    "telefone", "whatsapp", "siteAntigo", "motivo", "status", "urlNova",
    "dataProposta", "valor", "obs", "contratoStatus", "contratoEm",
    "manutencao", "pago", "docCliente", "endCliente",
]


@dataclass
class Lead:
    slug: str
    nome: str
    nicho: str | None = None
    cidade: str | None = None
    nota: float | None = None
    avaliacoes: int | None = None
    email: str | None = None
    telefone: str | None = None
    whatsapp: str | None = None
    siteAntigo: str | None = None
    motivo: str | None = None
    status: str = Estado.DESCOBERTO.value
    urlNova: str | None = None
    dataProposta: str | None = None
    valor: float | None = None
    obs: str | None = None
    contratoStatus: str | None = None
    contratoEm: str | None = None
    manutencao: float | None = None
    pago: int | None = None
    docCliente: str | None = None
    endCliente: str | None = None
    sem_portao: bool = False
    atualizado: str | None = None

    def para_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def de_dict(cls, d: dict) -> "Lead":
        campos = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in campos})
