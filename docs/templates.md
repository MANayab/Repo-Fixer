# Templates

Repo Fixer uses packaged Jinja2 templates in `repo_fixer/templates/`. Template rendering uses a Jinja `SandboxedEnvironment` with strict undefined values. Context values are limited to the project directory name, detected language, selected license identifier, and attribution text.

Generated Markdown/YAML contains a Repo Fixer attribution comment. Templates are starter material: review and customize workflow commands, support details, project-specific configuration, and contribution policies before use.

Language detection uses project manifests: `pyproject.toml` / `requirements.txt` / `setup.py` (Python), `package.json` (Node.js), `go.mod` (Go), and `Cargo.toml` (Rust). The first recognized marker in this priority order is selected. Unknown languages receive a language-neutral CI placeholder and .gitignore note.
