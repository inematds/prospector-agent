from prospector.descoberta.base import Candidato, passa_filtros_basicos, slugify


def test_filtros_reprova_nota_baixa_poucas_aval_ou_sem_site():
    assert passa_filtros_basicos(Candidato("A", "http://a.com", 4.8, 120))
    assert not passa_filtros_basicos(Candidato("B", "http://b.com", 4.5, 120))  # nota
    assert not passa_filtros_basicos(Candidato("C", "http://c.com", 4.9, 10))   # aval
    assert not passa_filtros_basicos(Candidato("D", None, 4.9, 120))            # sem site


def test_slugify():
    assert slugify("Clínica São José", "Bauru") == "clinica-sao-jose-bauru"
    assert slugify("Dr. Ana  Paula") == "dr-ana-paula"
