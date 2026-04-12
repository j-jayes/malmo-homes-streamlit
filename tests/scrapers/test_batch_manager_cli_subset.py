from pathlib import Path

from src.scrapers.batch_manager_cli import slice_input_subset


def test_slice_input_subset_skips_blank_urls(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    source.write_text("url\nhttps://www.hemnet.se/salda/a-1\n\n   \nhttps://www.hemnet.se/salda/b-2\n", encoding="utf-8")

    subset = tmp_path / "subset.csv"
    total, written, _ = slice_input_subset(source, subset)

    assert total == 3
    assert written == 2
    content = subset.read_text(encoding="utf-8")
    assert "https://www.hemnet.se/salda/a-1" in content
    assert "https://www.hemnet.se/salda/b-2" in content
