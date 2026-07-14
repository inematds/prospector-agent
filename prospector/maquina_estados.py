from __future__ import annotations
from prospector.modelos import Estado

E = Estado

TRANSICOES: dict[Estado, set[Estado]] = {
    E.DESCOBERTO: {E.QUALIFICADO, E.DESCARTADO},
    E.QUALIFICADO: {E.REDESENHADO, E.DESCARTADO},
    E.REDESENHADO: {E.PUBLICADO, E.ERRO},
    E.PUBLICADO: {E.AGUARDANDO_APROVACAO, E.ENVIADO, E.ERRO},
    E.AGUARDANDO_APROVACAO: {E.ENVIADO, E.DESCARTADO},
    E.ENVIADO: {E.RESPONDIDO, E.ERRO},
    E.RESPONDIDO: {E.FECHADO, E.DESCARTADO},
    E.FECHADO: set(),
    E.DESCARTADO: set(),
    E.ERRO: {E.QUALIFICADO, E.REDESENHADO, E.PUBLICADO, E.ENVIADO},  # /retry
}

_TERMINAIS = {E.FECHADO, E.DESCARTADO}


class TransicaoInvalida(Exception):
    pass


def transicoes_validas(estado: Estado) -> set[Estado]:
    return TRANSICOES.get(estado, set())


def pode_transicionar(de: Estado, para: Estado) -> bool:
    return para in transicoes_validas(de)


def eh_terminal(estado: Estado) -> bool:
    return estado in _TERMINAIS


def avancar(de: Estado, para: Estado) -> Estado:
    if not pode_transicionar(de, para):
        raise TransicaoInvalida(f"{de.value} -> {para.value} não é permitido")
    return para
