import pytest
from prospector import cli


def test_redesenhar_slug_inexistente_retorna_erro(tmp_path, capsys):
    rc = cli.main(["redesenhar", "nao-existe", "--db", str(tmp_path / "x.db")])
    assert rc == 1
    assert "não encontrado" in capsys.readouterr().out.lower() or \
           "nao encontrado" in capsys.readouterr().out.lower()


def test_subcomandos_registrados():
    parser_ok = cli.main  # smoke: main existe
    with pytest.raises(SystemExit):
        cli.main(["publicar"])  # falta o slug obrigatório -> argparse SystemExit
