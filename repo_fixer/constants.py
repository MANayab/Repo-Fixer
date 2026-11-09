"""Shared project constants."""
__version__ = "0.2.0"
CONFIG_FILENAME = "repo-fixer.yml"
DEFAULT_CONFIG = """license: MIT
project_name: My Project
project_description: A short description of the project.
default_branch: main
create_pull_request: true
generate:
  readme: true
  license: true
  contributing: true
  code_of_conduct: true
  issue_templates: true
  pull_request_template: true
  ci: true
  changelog: true
  gitignore: true
"""
