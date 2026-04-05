# Contract Generator

Generate a polished, fillable contract PDF from YAML.

## Install

```bash
pip install -e .
```

For test dependencies:

```bash
pip install -e .[dev]
```

## Usage

```bash
python generate_contract.py examples/model_release.yml output/model-release.pdf
```

Or via the installed console script:

```bash
contract-generator examples/model_release.yml output/model-release.pdf
```

List available templates:

```bash
contract-generator --list-templates
```

