import os
from prospector.modelos import Lead, Estado
from prospector.estado import db
from prospector.criacao.criador import Criador


def _fake_gera(lead, dest):
    with open(os.path.join(dest, "index.html"), "w", encoding="utf-8") as f:
        f.write(f"<html>{lead.nome} novo</html>")


def test_redesenhar_gera_arquivos_e_muda_status(tmp_path):
    conn = db.conectar(":memory:")
    lead = Lead(slug="clinica-x", nome="Clínica X", status=Estado.QUALIFICADO.value,
                siteAntigo="http://old.com", motivo="datado")
    db.salvar_lead(conn, lead)
    criador = Criador(_fake_gera, base_dir=str(tmp_path))
    dest = criador.redesenhar(lead, conn)
    assert os.path.exists(os.path.join(dest, "index.html"))
    assert os.path.exists(os.path.join(dest, "proposta.html"))
    assert db.ler_lead(conn, "clinica-x").status == "redesenhado"


def test_redesenhar_falha_se_index_vazio(tmp_path):
    conn = db.conectar(":memory:")
    lead = Lead(slug="y", nome="Y", status=Estado.QUALIFICADO.value)
    db.salvar_lead(conn, lead)
    criador = Criador(lambda l, d: None, base_dir=str(tmp_path))  # não escreve index
    try:
        criador.redesenhar(lead, conn)
        assert False, "deveria ter falhado"
    except RuntimeError:
        pass
