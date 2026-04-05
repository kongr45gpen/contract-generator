from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from contract_generator.render_pdf import generate_contract_pdf
from contract_generator.schema import ContractLoadError, load_contract_from_yaml
from contract_generator.template_registry import list_templates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a contract PDF from a YAML template.")
    parser.add_argument("input_yaml", nargs="?", help="Path to the YAML contract file.")
    parser.add_argument("output_pdf", nargs="?", help="Path where the generated PDF should be written.")
    parser.add_argument("--list-templates", action="store_true", help="List available templates and exit.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_templates:
        for template in list_templates():
            print(f"{template.name}: {template.description}")
        return 0

    if not args.input_yaml or not args.output_pdf:
        parser.error("input_yaml and output_pdf are required unless --list-templates is used")

    try:
        contract = load_contract_from_yaml(Path(args.input_yaml))
        generate_contract_pdf(contract, Path(args.output_pdf))
    except ContractLoadError as exc:
        parser.exit(status=2, message=f"error: {exc}\n")
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        parser.exit(status=1, message=f"error: {exc}\n")

    print(f"Wrote contract PDF to {args.output_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
