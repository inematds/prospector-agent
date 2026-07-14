import json
from prospector.descoberta.base import Candidato
from prospector.descoberta.fake import FakeDiscovery
from prospector.qualificacao.qualificador import Qualificador
from prospector.estado import db
from prospector.cli import prospectar


def test_prospectar_salva_so_qualificados():
    cands = [Candidato("Boa", "http://boa.com", 4.9, 100),
             Candidato("Ruim nota", "http://r.com", 4.0, 100)]  # reprova filtro
    prov = FakeDiscovery(cands)
    veredito = json.dumps({"site_ruim": True, "motivo": "datado", "email": "a@boa.com"})
    q = Qualificador(lambda p: veredito, lambda u: "<html/>")
    conn = db.conectar(":memory:")
    salvos = prospectar(prov, q, conn, "nutri", "Bauru", meta=10)
    assert [l.slug for l in salvos] == ["boa"]
    assert db.ler_lead(conn, "boa").status == "qualificado"
