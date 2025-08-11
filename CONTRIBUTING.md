# Contributing Guide

Thanks for your interest in contributing! This guide helps you get started quickly and keep contributions consistent.

## Ways to contribute
- Report bugs and propose features via issues
- Improve documentation and examples
- Fix bugs or add enhancements

## Development setup
1. Fork and clone the repo
2. Create a new branch from `main`: `git checkout -b feat/your-feature`
3. Prepare environment:
   - Copy `.env.example` to `.env` and fill secrets
   - Backend: Python 3.11+, `pip install -r backend/requirements.txt`
   - Frontend: Node 18+, `npm install` in `frontend/`
4. Run locally:
   - `./start-dev.sh` (recommended) or run backend/frontend separately
5. Run tests where applicable (e.g., `pytest` under `backend/`)

## Commit style
Use clear, descriptive commits. Conventional Commits are encouraged:
- `feat:` new feature
- `fix:` bug fix
- `docs:` docs changes
- `refactor:` refactoring
- `test:` add or update tests
- `chore:` tooling, CI, dependencies

## Pull Requests
- Keep PRs focused and small when possible
- Update docs/tests accordingly
- Describe the changes, motivation, and any breaking changes
- Link related issues (e.g., `Closes #123`)

## Code of Conduct
By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

