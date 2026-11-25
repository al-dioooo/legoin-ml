from pathlib import Path

from tools.labeler.files import NOTEBOOK_DATA, default_root


def test_default_root_is_next_to_the_notebooks(monkeypatch):
    monkeypatch.delenv("LEGOIN_DATA_DIR", raising=False)
    assert default_root() == NOTEBOOK_DATA / "foto_mandiri"
    assert NOTEBOOK_DATA == Path(__file__).resolve().parents[3] / "notebooks" / "data"


def test_default_root_follows_legoin_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("LEGOIN_DATA_DIR", str(tmp_path))
    assert default_root() == tmp_path / "foto_mandiri"


def test_default_root_expands_home(monkeypatch):
    monkeypatch.setenv("LEGOIN_DATA_DIR", "~/ml-datasets")
    assert default_root() == Path.home() / "ml-datasets" / "foto_mandiri"


def test_empty_legoin_data_dir_is_ignored(monkeypatch):
    monkeypatch.setenv("LEGOIN_DATA_DIR", "")
    assert default_root() == NOTEBOOK_DATA / "foto_mandiri"
