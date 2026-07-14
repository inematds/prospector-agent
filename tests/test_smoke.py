import prospector


def test_versao_exposta():
    assert isinstance(prospector.__version__, str)
    assert prospector.__version__
