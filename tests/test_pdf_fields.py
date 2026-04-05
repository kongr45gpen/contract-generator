from pathlib import Path

from contract_generator.render_pdf import generate_contract_pdf
from contract_generator.schema import load_contract_from_yaml
from pypdf import PdfReader


def _field_map(reader: PdfReader) -> dict[str, object]:
    acroform = reader.trailer["/Root"].get("/AcroForm")
    assert acroform is not None
    fields = acroform.get_object()["/Fields"]
    result: dict[str, object] = {}
    for field in fields:
        field_obj = field.get_object()
        name = field_obj.get("/T")
        if name:
            result[str(name)] = field_obj
    return result


def test_generated_pdf_contains_editable_fields_and_signature(tmp_path: Path) -> None:
    contract = load_contract_from_yaml(Path("contract_generator/templates/model_release.yml"))
    output = tmp_path / "model-release.pdf"

    generate_contract_pdf(contract, output)

    reader = PdfReader(str(output))
    fields = _field_map(reader)

    assert "subject_name" in fields
    assert "project_name" in fields
    assert "effective_date" in fields
    assert "usage_scope" in fields
    assert "subject_signature" in fields
    assert fields["subject_signature"].get("/FT") == "/Sig"
