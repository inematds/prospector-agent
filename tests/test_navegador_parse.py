from prospector.descoberta.navegador import _candidato_de_dados


def test_parse_card_extrai_campos():
    c = _candidato_de_dados({"nome": "Clínica X", "site": "http://x.com",
                             "nota": "4,8", "avaliacoes": "1.234", "telefone": "(14) 99999-0000"})
    assert c.nome == "Clínica X"
    assert c.nota == 4.8            # vírgula decimal BR -> float
    assert c.avaliacoes == 1234     # milhar BR removido
    assert c.site_url == "http://x.com"
    assert c.fonte == "navegador"


def test_parse_card_campos_ausentes():
    c = _candidato_de_dados({"nome": "Só Nome"})
    assert c.nome == "Só Nome" and c.nota is None and c.site_url is None
