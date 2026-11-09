# Usage

## Audit

`repo-fixer scan [REPOSITORY]` prints findings. Add `--format json` for machine-readable output. `repo-fixer score [REPOSITORY]` prints the readiness score and accepts the same output option.

## Fix

```bash
repo-fixer fix --dry-run
repo-fixer fix
repo-fixer fix --path ./my-project
repo-fixer fix --yes
repo-fixer fix --license MIT
repo-fixer fix --force
```

- `--path PATH`: repository directory (defaults to the current directory).
- `--dry-run`: show the plan; no files or directories are created.
- `--yes`: skip the normal confirmation for new-file creation only.
- `--license`: explicit license choice when LICENSE is missing.
- `--force`: permit replacement of an existing weak README only after a separate confirmation and timestamped backup. It does not bypass the confirmation, even with `--yes`.

A weak existing README is preserved and a proposed alternative is written as `repo-fixer-proposed-README.md` only after confirmation. Review and rename it manually if desired. Existing files are skipped by default.
