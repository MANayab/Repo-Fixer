# Usage

## Audit

`repo-fixer scan [REPOSITORY]` prints findings. Add `--format json` for machine-readable output. `repo-fixer score [REPOSITORY]` prints the readiness score and accepts the same output option.

## Local fix

```bash
repo-fixer fix --dry-run
repo-fixer fix
repo-fixer fix --path ./my-project
repo-fixer fix --yes
repo-fixer fix --license MIT
repo-fixer fix --force
```

- `--path PATH`: repository directory (defaults to the current directory).
- `--dry-run`: show the plan; no files or directories are created and GitHub is not contacted.
- `--yes`: skip the normal confirmation for new-file creation only.
- `--license`: explicit license choice when LICENSE is missing.
- `--force`: permit local replacement of an existing weak README only after a separate confirmation and timestamped backup.

A weak existing README is preserved and a proposed alternative is written as `repo-fixer-proposed-README.md`. Existing files are skipped by default.

## Create a GitHub pull request

```powershell
$env:GITHUB_TOKEN = "github_pat_..."
repo-fixer fix --create-pr --license MIT
```

Set `GITHUB_TOKEN` to a fine-grained token with Contents read/write and Pull requests read/write on the target repository (Metadata read-only is mandatory). Repo Fixer resolves the repository from `GITHUB_REPOSITORY=owner/name` or the local checkout's `origin` remote. It previews the planned additions and asks before creating one pull request; `--yes` skips that confirmation. `--dry-run` never contacts GitHub.

The PR uses a new `repo-fixer/improvements-...` branch and targets the repository's default branch. Only new paths are committed. Existing remote paths stop the operation. `--force` cannot be combined with `--create-pr`. No direct default-branch push, force-push, file deletion, overwrite, or automatic merge is possible.

See [GitHub integration](github-integration.md) for permissions, behavior, and error handling.
