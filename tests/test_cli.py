from pathlib import Path

from contract_generator.cli import main
from pypdf import PdfReader


def test_cli_writes_pdf(tmp_path: Path) -> None:
    output = tmp_path / "release.pdf"
    sample_yaml = Path("contract_generator/templates/model_release.yml")

    exit_code = main([str(sample_yaml), str(output)])

    assert exit_code == 0
    assert output.exists()

    reader = PdfReader(str(output))
    assert len(reader.pages) == 1
