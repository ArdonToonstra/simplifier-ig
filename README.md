# simplifier-ig

CLI tool for generating [Simplifier.net](https://simplifier.net) Implementation Guide structures. A Python port of functionality from Firely Terminal.

## Installation

```bash
pip install simplifier-ig
```

Or install from source:

```bash
git clone https://github.com/ArdonToonstra/simplifier-ig.git
cd simplifier-ig
pip install .
```

## Usage

### Initialize a new IG input folder

```bash
simplifier-ig init --path ./my-ig --name "My Implementation Guide"
```

| Option    | Description                              | Default                      |
|-----------|------------------------------------------|------------------------------|
| `--path`  | Where to create the IG input structure   | `./input`                    |
| `--name`  | Name for the Implementation Guide        | `My Implementation Guide`    |
| `--style` | Style folder name                        | `custom`                     |
| `--force` | Allow init in a non-empty directory      |                              |

### Validate an IG input folder

```bash
simplifier-ig validate --input ./my-ig
```

### Generate an IG

```bash
simplifier-ig generate --input ./my-ig --output ./output
```

By default, an `ImplementationGuide.json` FHIR R4 resource is generated alongside the IG. This requires the following fields in `guide.yaml`:

```yaml
id: my.ig.id
status: draft          # draft | active | retired | unknown
fhirVersion: 4.0.1
canonical: https://example.org/fhir
```

If these fields are missing, the tool warns and skips IG resource generation automatically.

| Option               | Description                                      | Default  |
|----------------------|--------------------------------------------------|----------|
| `--input`            | Path to the input folder                         | saved path or `./input` |
| `--output`           | Path to the output folder                        | `./guides` |
| `--skip-validation`  | Skip input validation                            |          |
| `--no-ig-resource`   | Skip ImplementationGuide.json resource generation |         |

### Generate IG resource separately

```bash
simplifier-ig ig-resource --path ./output/my-ig --input ./my-ig
```

### Configuration

```bash
simplifier-ig config   # Show current configuration
simplifier-ig clear    # Clear saved configuration
```

## Input folder structure

After running `init`, the input folder will have this structure:

```
my-ig/
├── guide.yaml                  # IG configuration (title, url-key, menu, etc.)
├── variables.yaml              # Template variables
├── resources/                  # FHIR conformance resources (.json)
├── examples/                   # FHIR example resources (.json)
├── pages/                      # Markdown documentation pages
├── images/                     # (optional) Images
├── pagetemplates/              # (optional) Reusable page snippets
├── pagetemplates-artifacts/    # Per-resource-type page templates
└── styles/
    └── custom/
        ├── master.html
        ├── settings.style
        └── style.css
```

## Development

```bash
git clone https://github.com/ArdonToonstra/simplifier-ig.git
cd simplifier-ig
pip install -e .
```

You can also run the tool as a module:

```bash
python -m simplifier_ig --help
```

### Building binaries

The GitHub Actions workflow builds standalone binaries for Linux, macOS, and Windows using PyInstaller on every push to `main`.

### Publishing to PyPI

Tag a release to trigger the publish workflow:

```bash
git tag v0.1.0
git push origin v0.1.0
```

This requires a `PYPI_API_TOKEN` secret configured in the repository settings.

## Dependencies

- Python >= 3.9
- [PyYAML](https://pypi.org/project/PyYAML/)

## License

MIT
