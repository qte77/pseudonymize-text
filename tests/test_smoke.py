import pseudonymize_text
from pseudonymize_text import cli


def test_package_exposes_version() -> None:
    assert isinstance(pseudonymize_text.__version__, str)
    assert pseudonymize_text.__version__


def test_cli_main_is_callable() -> None:
    assert callable(cli.main)
