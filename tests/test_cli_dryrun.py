from prospector.modelos import Lead, Estado
from prospector import cli


def test_caminho_com_portao_para_em_aprovacao():
    caminho = cli.caminho_dry_run(Lead(slug="c", nome="C", sem_portao=False))
    assert Estado.AGUARDANDO_APROVACAO in caminho
    assert Estado.ENVIADO not in caminho


def test_caminho_auto_vai_ate_enviado():
    caminho = cli.caminho_dry_run(Lead(slug="c", nome="C", sem_portao=True))
    assert Estado.AGUARDANDO_APROVACAO not in caminho
    assert caminho[-1] == Estado.ENVIADO


def test_demo_dry_run_nao_cria_db(tmp_path, capsys):
    db_file = tmp_path / "x.db"
    rc = cli.main(["demo", "--dry-run", "--auto", "--db", str(db_file)])
    assert rc == 0
    assert not db_file.exists()            # dry-run não toca disco
    out = capsys.readouterr().out
    assert "enviado" in out                # imprimiu o caminho
