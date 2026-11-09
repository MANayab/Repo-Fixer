# Safety guarantees

- `scan`, `score`, and `fix --dry-run` do not modify repository files.
- `fix` previews planned changes and requires confirmation before creating files unless `--yes` is explicitly supplied.
- New files use exclusive creation; a file that appears between planning and writing is not overwritten.
- Existing files are skipped. A weak README is proposed as `repo-fixer-proposed-README.md`; replacement requires `--force` and a second explicit confirmation.
- A timestamped backup is created before an approved replacement.
- LICENSE generation requires an explicit license selection; no default is inferred.
- Symlinks are rejected in target paths; writes are confined to the resolved repository root.
- No files are deleted. No GitHub API, authentication, branch, commit, pull-request, network, AI-service, or database functionality is part of v0.3.0.

Repo Fixer cannot eliminate all filesystem races on every platform. Run it with ordinary user permissions, inspect the preview, and review generated files before committing them.
