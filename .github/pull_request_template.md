## What and why

<!-- What does this change do, and which problem does it solve? Link the issue: Closes #… -->

## How it was tested

<!-- Tests added or changed, manual checks. -->

## Checklist

- [ ] Every commit is signed off (`git commit -s`), certifying the
      [Developer Certificate of Origin](https://developercertificate.org/). See CONTRIBUTING.md.
- [ ] Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/).
- [ ] `uv run ruff check`, `uv run ruff format --check`, `uv run pyright` and `uv run pytest` pass.
- [ ] No real data, names, tenant, site, group or app IDs, and no secrets.
- [ ] User-visible texts are in `locales/de` and `locales/en`, not in code.
- [ ] Modules only import `campus_agent_core.ports`; no tool takes a user ID parameter.
- [ ] A fundamental decision is recorded as an ADR in `docs/adr/` (if applicable).
- [ ] CHANGELOG.md is updated under "Unreleased" (if user-facing).
