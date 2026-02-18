# simplifier-ig

CLI tool for generating [Simplifier.net](https://simplifier.net) Implementation Guide structures from a IG publisher like input folder. The tool supports initializing a new IG input structure, validating the input, and generating the IG output. It also allows saving configuration for repeated use.

## Installation

### Via pip (recommended for developers)

```bash
pip install simplifier-ig
```

### Via standalone binary (no Python required)

Download the pre-built binary for your OS from the [GitHub Actions artifacts](https://github.com/ArdonToonstra/simplifier-ig/actions/workflows/build.yml):

1. Go to the **Actions** tab → **Build Binaries** workflow
2. Click on the latest successful run (tagged with a version like `v0.1.0`)
3. Scroll down to **Artifacts** and download:
   - `simplifier-ig-linux` (Linux)
   - `simplifier-ig-macos` (macOS)
   - `simplifier-ig-windows` (Windows)
4. Extract the binary and make it executable (Linux/macOS only):
   ```bash
   # Linux/macOS
   chmod +x simplifier-ig
   ./simplifier-ig --help
   
   # Or add to PATH
   sudo mv simplifier-ig /usr/local/bin/
   ```
   
   ```powershell
   # Windows (PowerShell)
   .\simplifier-ig.exe --help
   
   # Or add to PATH by moving to a directory in your PATH
   ```

> **Note**: Binaries are currently stored as GitHub Actions artifacts (90-day retention). For permanent releases, they can be manually attached to GitHub Releases or automated via an additional workflow.

### From source

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

The GitHub Actions workflow builds standalone binaries for Linux, macOS, and Windows using PyInstaller when a version tag is pushed (e.g., `v0.1.0`).

**To build binaries for a release:**

```bash
git tag v0.1.0
git push origin v0.1.0
```

This triggers the **Build Binaries** workflow which creates three artifacts:
- `simplifier-ig-linux` (Ubuntu)
- `simplifier-ig-macos` (macOS)
- `simplifier-ig-windows` (Windows .exe)

Artifacts are available in the **Actions** tab → **Build Binaries** workflow for 90 days. To attach binaries permanently to GitHub Releases, either:
- Download artifacts and manually attach to the release, or
- Extend the workflow to automatically create a GitHub Release with attached binaries

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
