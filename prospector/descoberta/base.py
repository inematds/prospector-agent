from __future__ import annotations
import re
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Candidato:
    nome: str
    site_url: str | None = None
    nota: float | None = None
    avaliacoes: int | None = None
    telefone: str | None = None
    whatsapp: str | None = None
    fonte: str = "?"


class DiscoveryProvider(ABC):
    @abstractmethod
    def descobrir(self, nicho: str, cidade: str, meta: int) -> list["Candidato"]:
        ...


def passa_filtros_basicos(c: Candidato, nota_min: float = 4.7, aval_min: int = 40) -> bool:
    return bool(c.site_url) and (c.nota or 0) >= nota_min and (c.avaliacoes or 0) >= aval_min


def slugify(nome: str, cidade: str | None = None) -> str:
    base = f"{nome} {cidade}" if cidade else nome
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    return re.sub(r"-+", "-", base)
