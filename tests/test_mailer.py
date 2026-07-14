from prospector.modelos import Lead, Estado
from prospector.estado import db
from prospector.envio.mailer import Mailer, Supressao


def _lead(status="publicado"):
    return Lead(slug="c", nome="X", email="a@x.com", urlNova="http://new.com", status=status)


def test_envio_normal_grava_estado_e_optout():
    enviados = []
    m = Mailer(lambda to, a, h: enviados.append((to, h)) or "mid-1", Supressao(), "from@cold.com")
    conn = db.conectar(":memory:"); lead = _lead(); db.salvar_lead(conn, lead)
    mid = m.enviar(lead, conn)
    assert mid == "mid-1"
    assert enviados[0][0] == "a@x.com"
    assert "opt-out" in enviados[0][1].lower() or "descadastr" in enviados[0][1].lower()
    assert db.ler_lead(conn, "c").status == "enviado"


def test_suprimido_nao_envia():
    enviados = []
    m = Mailer(lambda to, a, h: enviados.append(to) or "x", Supressao({"a@x.com"}), "from@cold.com")
    conn = db.conectar(":memory:"); lead = _lead(); db.salvar_lead(conn, lead)
    assert m.enviar(lead, conn) is None
    assert enviados == []
    assert db.ler_lead(conn, "c").status == "publicado"  # inalterado


def test_estado_invalido_levanta():
    m = Mailer(lambda to, a, h: "x", Supressao(), "from@cold.com")
    conn = db.conectar(":memory:"); lead = _lead(status="qualificado"); db.salvar_lead(conn, lead)
    try:
        m.enviar(lead, conn); assert False
    except Exception:
        pass
