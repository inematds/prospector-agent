import json
import pytest
from prospector import config as cfg


def test_carregar_config(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({
        "nichos": ["nutricionistas", "advogados"],
        "meta_leads": 10,
        "dominio_publicacao": "exemplo.com",
        "from_email": "contato@cold.exemplo.com",
        "db_path": "prospector.db",
    }), encoding="utf-8")
    c = cfg.carregar_config(str(p))
    assert c.nichos == ["nutricionistas", "advogados"]
    assert c.meta_leads == 10
    assert c.db_path == "prospector.db"


def test_config_usa_defaults_quando_faltando(tmp_path):
    p = tmp_path / "config.json"
    p.write_text("{}", encoding="utf-8")
    c = cfg.carregar_config(str(p))
    assert c.meta_leads == 10          # default
    assert c.nichos == []
    assert c.db_path == "prospector.db"


def test_segredo_exigir_ausente_levanta(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    with pytest.raises(cfg.SegredoAusente):
        cfg.Segredos.exigir("RESEND_API_KEY")


def test_segredo_exigir_presente(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_123")
    assert cfg.Segredos.exigir("RESEND_API_KEY") == "re_123"
