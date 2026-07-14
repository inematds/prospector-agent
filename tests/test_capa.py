from prospector.modelos import Lead
from prospector.criacao.capa import montar_capa


def test_capa_contem_dados_do_lead():
    lead = Lead(slug="c", nome="Clínica X", siteAntigo="http://old.com",
                urlNova="http://new.com", motivo="layout datado")
    html = montar_capa(lead)
    assert "<!DOCTYPE html>" in html or "<!doctype html>" in html.lower()
    assert "Clínica X" in html
    assert "http://old.com" in html and "http://new.com" in html
    assert "layout datado" in html


def test_capa_sem_url_nova_avisa():
    html = montar_capa(Lead(slug="c", nome="Y", siteAntigo="http://o.com"))
    assert "http://o.com" in html
    assert "não publicad" in html.lower() or "nao publicad" in html.lower()
