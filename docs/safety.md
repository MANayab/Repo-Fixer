# Safety guarantees

- `scan`, `score`, and `fix --dry-run` do not modify repository files or contact GitHub.
- Local `fix` previews planned changes and requires confirmation before creating files unless `--yes` is explicitly supplied.
- New local files use exclusive creation; a file that appears between planning and writing is not overwritten.
- Existing local files are skipped. A weak README is proposed separately; local replacement requires `--force`, a second explicit confirmation, and a timestamped backup.
- LICENSE generation requires an explicit license selection; no default is inferred.
- Local symlink targets are rejected and writes are confined to the selected repository root.
- `fix --create-pr` requires an explicit token in `GITHUB_TOKEN` and confirmation unless `--yes` is supplied.
- GitHub changes are additions-only on a uniquely named feature branch. Existing remote paths are checked and cause the operation to stop rather than overwrite.
- The GitHub integration never pushes to the default branch, force-pushes, deletes files, or merges pull requests.
- GitHub API tests are mocked; CI does not use credentials or call GitHub's API.

Use a fine-grained token restricted to the target repository with Contents read/write and Pull requests read/write, plus GitHub's mandatory Metadata read-only permission. Never store tokens in project configuration or source control.

Repo Fixer cannot eliminate all filesystem or remote repository races on every platform. Inspect the preview and generated content, and run the target project's checks before merging a pull request.
