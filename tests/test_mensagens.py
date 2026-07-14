import pytest
from prospector.modelos import Lead
from prospector.canal.mensagens import parse_prospectar, msg_pedir_aprovacao, msg_enviado


def test_parse_com_e_sem_auto():
    assert parse_prospectar("/prospectar nutricionistas Bauru --auto") == ("nutricionistas", "Bauru", True)
    assert parse_prospectar("/prospectar advogados Marilia") == ("advogados", "Marilia", False)


def test_parse_faltando_cidade_levanta():
    with pytest.raises(ValueError):
        parse_prospectar("/prospectar nutri")


def test_mensagens_incluem_dados():
    lead = Lead(slug="c", nome="Clínica X", motivo="datado", urlNova="http://new.com", email="a@x.com")
    assert "Clínica X" in msg_pedir_aprovacao(lead) and "http://new.com" in msg_pedir_aprovacao(lead)
    assert "a@x.com" in msg_enviado(lead)
