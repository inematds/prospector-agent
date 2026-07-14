import pytest
from prospector import cli


def test_aprovar_slug_inexistente(tmp_path, capsys):
    rc = cli.main(["aprovar", "nao-existe", "--db", str(tmp_path / "x.db")])
    assert rc == 1
    out = capsys.readouterr().out.lower()
    assert "não encontrado" in out or "nao encontrado" in out


def test_atender_precisa_nicho_cidade():
    with pytest.raises(SystemExit):
        cli.main(["atender", "nutri"])   # falta cidade -> argparse
