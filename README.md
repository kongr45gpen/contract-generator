# Contract Generator

Generate a polished, fillable contract PDF from YAML.

The first built-in template is a model release form with editable form fields and a true PDF signature field.

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

## YAML Format

The YAML root has three keys:
- `template`: which template to render
- `template_parameters`: values used by that template
- `generic_parameters`: model-independent options shared across templates

Example:

```yaml
template: model_release
template_parameters:
	document_title: Model Release Form
	subject_name: Jordan Avery
	project_name: Atlas Spring Campaign
	effective_date: 2026-04-05
	location: Austin, Texas
	company_name: Northstar Media LLC
	email: jordan.avery@example.com
	usage_scope: All media, worldwide, in perpetuity
	consideration: Included in project fee
	governing_law: California
	notes: Optional shoot notes can go here.
generic_parameters:
	header: "Internal use `MR-2026-001`"
	footer: ""
```

The optional generic `header` is parsed as inline markdown. Backtick code segments are rendered in a black-and-white monospace style.

## Customization

The current implementation ships with a reusable model release template. The code is organized so that additional contract templates can be added by defining a new template module, input schema, and field layout.
