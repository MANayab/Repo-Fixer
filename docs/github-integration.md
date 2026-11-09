# GitHub integration

Repo Fixer can optionally create a reviewable pull request with generated repository improvements.

## Token permissions

Create a fine-grained personal access token limited to the target repository with:

- **Contents: Read and write** — inspect the repository tree, create blobs/trees/commits, and create a feature branch.
- **Pull requests: Read and write** — open the proposed pull request.
- **Metadata: Read-only** — GitHub's mandatory repository metadata access.

Do not grant Administration, Actions, Workflows, Issues, or organization permissions. Store the token in the `GITHUB_TOKEN` environment variable. Never paste it into command arguments, configuration files, source control, or logs.

## Usage

From a local checkout with a GitHub `origin` remote:

```bash
# Windows PowerShell
$env:GITHUB_TOKEN = "github_pat_..."
repo-fixer fix --create-pr --license MIT

# Or identify the target explicitly (useful in CI)
$env:GITHUB_REPOSITORY = "owner/repository"
repo-fixer fix --create-pr --yes
```

The command previews the proposed paths and asks for confirmation unless `--yes` is supplied. `--dry-run` never contacts GitHub. Existing remote paths are checked and cause the operation to stop rather than overwrite. All changes are additions on a uniquely named `repo-fixer/improvements-...` branch, followed by one pull request to the repository's default branch.

The integration never pushes to the default branch, force-pushes, deletes files, replaces existing files, or merges pull requests. Review generated content and run project checks before merging.

## Error handling

Invalid/expired tokens, missing Contents permission, GitHub permission failures, missing resources, API failures, and rate limits produce distinct actionable errors. GitHub's `Retry-After` or rate-limit reset time is shown when available. Mutating requests are not automatically retried to avoid duplicate branches, commits, or pull requests.

A token's fine-grained Pull requests permission cannot be reliably introspected before attempting the PR endpoint. If that permission is missing, GitHub rejects PR creation with a clear permission error; the created feature branch is retained for inspection and is never deleted automatically.

## CI testing

The integration tests mock the API client boundary. CI does not use a real token or make live GitHub API calls.
