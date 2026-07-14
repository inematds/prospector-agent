import json
from prospector.descoberta.base import Candidato
from prospector.qualificacao.qualificador import Qualificador


def _llm(resp): return lambda prompt: resp
def _site(html="<html>site</html>"): return lambda url: html
BOM = Candidato("Boa Clínica", "http://boa.com", 4.9, 200)


def test_site_ruim_com_email_vira_lead():
    veredito = json.dumps({"site_ruim": True, "motivo": "layout datado, sem CTA",
                           "email": "contato@boa.com", "whatsapp": "5514999990000"})
    q = Qualificador(_llm("veredito: " + veredito), _site())
    lead = q.qualificar(BOM)
    assert lead is not None
    assert lead.status == "qualificado"
    assert lead.email == "contato@boa.com"
    assert lead.motivo and lead.siteAntigo == "http://boa.com"
    assert lead.slug == "boa-clinica"


def test_site_bom_descarta():
    q = Qualificador(_llm(json.dumps({"site_ruim": False, "motivo": "", "email": "x@y.com"})), _site())
    assert q.qualificar(BOM) is None


def test_sem_email_descarta():
    q = Qualificador(_llm(json.dumps({"site_ruim": True, "motivo": "ruim", "email": None})), _site())
    assert q.qualificar(BOM) is None


def test_reprova_filtro_nao_chama_llm():
    chamado = []
    q = Qualificador(lambda p: chamado.append(1) or "{}", _site())
    assert q.qualificar(Candidato("X", "http://x.com", 4.0, 5)) is None
    assert chamado == []   # nem buscou site nem LLM
