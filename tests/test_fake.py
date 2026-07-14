from prospector.descoberta.base import Candidato
from prospector.descoberta.fake import FakeDiscovery


def test_fake_retorna_ate_meta_com_fonte():
    cands = [Candidato(f"N{i}", f"http://n{i}.com", 4.8, 50) for i in range(5)]
    prov = FakeDiscovery(cands)
    r = prov.descobrir("nutri", "Bauru", meta=3)
    assert len(r) == 3
    assert all(c.fonte == "fake" for c in r)
