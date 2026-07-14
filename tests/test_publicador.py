from prospector.modelos import Lead, Estado
from prospector.estado import db
from prospector.publicacao.github_pages import Publicador


def test_publicar_chama_boundary_grava_url_e_status():
    chamadas = []
    pub = Publicador(lambda local, slug: chamadas.append((local, slug)),
                     base_url="https://inematds.github.io/prospector-sites")
    conn = db.conectar(":memory:")
    lead = Lead(slug="clinica-x", nome="X", status=Estado.REDESENHADO.value)
    db.salvar_lead(conn, lead)
    url = pub.publicar(lead, conn, local_dir="sites/clinica-x")
    assert url == "https://inematds.github.io/prospector-sites/clinica-x/"
    assert chamadas == [("sites/clinica-x", "clinica-x")]
    lido = db.ler_lead(conn, "clinica-x")
    assert lido.status == "publicado" and lido.urlNova == url


def test_publicar_recusa_estado_invalido():
    pub = Publicador(lambda l, s: None, base_url="http://x")
    conn = db.conectar(":memory:")
    lead = Lead(slug="y", nome="Y", status=Estado.QUALIFICADO.value)  # não pode publicar
    db.salvar_lead(conn, lead)
    try:
        pub.publicar(lead, conn, "sites/y")
        assert False
    except Exception:
        pass
