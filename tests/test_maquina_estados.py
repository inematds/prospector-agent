import pytest
from prospector.modelos import Estado
from prospector import maquina_estados as me


def test_transicoes_lineares_validas():
    assert me.pode_transicionar(Estado.DESCOBERTO, Estado.QUALIFICADO)
    assert me.pode_transicionar(Estado.PUBLICADO, Estado.AGUARDANDO_APROVACAO)
    assert me.pode_transicionar(Estado.PUBLICADO, Estado.ENVIADO)  # rota --auto
    assert me.pode_transicionar(Estado.AGUARDANDO_APROVACAO, Estado.ENVIADO)


def test_descarte_e_erro():
    assert me.pode_transicionar(Estado.QUALIFICADO, Estado.DESCARTADO)
    assert me.pode_transicionar(Estado.REDESENHADO, Estado.ERRO)


def test_transicao_invalida_levanta():
    assert not me.pode_transicionar(Estado.DESCOBERTO, Estado.ENVIADO)
    with pytest.raises(me.TransicaoInvalida):
        me.avancar(Estado.DESCOBERTO, Estado.ENVIADO)


def test_avancar_valido_retorna_destino():
    assert me.avancar(Estado.DESCOBERTO, Estado.QUALIFICADO) == Estado.QUALIFICADO


def test_terminais():
    assert me.eh_terminal(Estado.FECHADO)
    assert me.eh_terminal(Estado.DESCARTADO)
    assert not me.eh_terminal(Estado.PUBLICADO)
