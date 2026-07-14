from __future__ import annotations
from dataclasses import replace
from prospector.descoberta.base import Candidato, DiscoveryProvider


class FakeDiscovery(DiscoveryProvider):
    def __init__(self, candidatos: list[Candidato]):
        self._candidatos = candidatos

    def descobrir(self, nicho: str, cidade: str, meta: int) -> list[Candidato]:
        return [replace(c, fonte="fake") for c in self._candidatos[:meta]]
