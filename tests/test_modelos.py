from prospector.modelos import Estado, Lead, CAMPOS


def test_estado_valores_minusculos():
    assert Estado.DESCOBERTO.value == "descoberto"
    assert Estado.AGUARDANDO_APROVACAO.value == "aguardando_aprovacao"
    assert Estado.ERRO.value == "erro"


def test_campos_inclui_schema_referencia():
    for c in ["slug", "nome", "nota", "email", "status", "urlNova", "manutencao"]:
        assert c in CAMPOS


def test_lead_default_e_roundtrip():
    lead = Lead(slug="clinica-x", nome="Clínica X")
    assert lead.status == "descoberto"
    assert lead.sem_portao is False
    d = lead.para_dict()
    assert d["slug"] == "clinica-x"
    assert Lead.de_dict(d).nome == "Clínica X"
