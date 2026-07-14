from prospector.modelos import Lead, Estado
from prospector.estado import db


def test_salvar_ler_e_upsert_idempotente():
    conn = db.conectar(":memory:")
    db.salvar_lead(conn, Lead(slug="c1", nome="Clínica 1", nota=4.8))
    # Reinserir o mesmo slug NÃO duplica (idempotência) e atualiza campos.
    db.salvar_lead(conn, Lead(slug="c1", nome="Clínica 1", nota=4.9))
    lido = db.ler_lead(conn, "c1")
    assert lido is not None
    assert lido.nota == 4.9
    assert len(db.listar_por_status(conn, Estado.DESCOBERTO.value)) == 1


def test_atualizar_status_e_carimbo():
    conn = db.conectar(":memory:")
    db.salvar_lead(conn, Lead(slug="c2", nome="Clínica 2"))
    db.atualizar_status(conn, "c2", Estado.QUALIFICADO.value)
    lido = db.ler_lead(conn, "c2")
    assert lido.status == "qualificado"
    assert lido.atualizado is not None


def test_ler_inexistente_retorna_none():
    conn = db.conectar(":memory:")
    assert db.ler_lead(conn, "nao-existe") is None
