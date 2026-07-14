import os
from prospector.modelos import Lead, Estado
from prospector.estado import db
from prospector.criacao.criador import Criador
from prospector.publicacao.github_pages import Publicador
from prospector.envio.mailer import Mailer, Supressao
from prospector.orquestrador.nucleo import Orquestrador


def _gera(lead, dest):
    with open(os.path.join(dest, "index.html"), "w", encoding="utf-8") as f:
        f.write("<html>ok</html>")


def _monta(tmp_path, enviados, notifs):
    return Orquestrador(
        criador=Criador(_gera, base_dir=str(tmp_path)),
        publicador=Publicador(lambda local, slug: None, "http://pages"),
        mailer=Mailer(lambda to, a, h: enviados.append(to) or "mid", Supressao(), "from@x"),
        notificar=lambda msg: notifs.append(msg),
        conn=None,  # setado abaixo
    )


def test_auto_vai_ate_enviado(tmp_path):
    conn = db.conectar(":memory:")
    enviados, notifs = [], []
    orq = _monta(tmp_path, enviados, notifs); orq._conn = conn
    lead = Lead(slug="x", nome="X", email="a@x.com", siteAntigo="http://o",
                status=Estado.QUALIFICADO.value, sem_portao=True)
    db.salvar_lead(conn, lead)
    orq.processar(lead)
    assert db.ler_lead(conn, "x").status == "enviado"
    assert enviados == ["a@x.com"]


def test_portao_para_em_aprovacao_e_aprovar_envia(tmp_path):
    conn = db.conectar(":memory:")
    enviados, notifs = [], []
    orq = _monta(tmp_path, enviados, notifs); orq._conn = conn
    lead = Lead(slug="y", nome="Y", email="b@y.com", siteAntigo="http://o",
                status=Estado.QUALIFICADO.value, sem_portao=False)
    db.salvar_lead(conn, lead)
    orq.processar(lead)
    assert db.ler_lead(conn, "y").status == "aguardando_aprovacao"
    assert enviados == []          # ainda não enviou
    assert any("Aprovar" in n for n in notifs)
    orq.aprovar("y")
    assert db.ler_lead(conn, "y").status == "enviado"
    assert enviados == ["b@y.com"]
