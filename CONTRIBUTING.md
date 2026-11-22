# Contributing

Thank you for helping improve 42 Team Finder. Contributions are accepted through fork-based pull requests; you do not need direct repository access.

## Development workflow

1. Fork the repository and create a focused branch from `master`.
2. Copy `.env.example` to `.env`. Never commit real credentials.
3. Start the application with `make up`.
4. Make a small, documented change with relevant tests.
5. Run `make test` before opening a pull request.
6. Open a pull request and complete the verification checklist.

Maintainers review and merge pull requests after required checks pass. Please avoid unrelated formatting or dependency changes in the same pull request.

## Privacy and security

- Never commit 42 API credentials, OAuth secrets, cookies, SSH keys, `.env`, or production configuration.
- Never add production databases, API responses containing student records, or screenshots with identifiable student data.
- Use synthetic fixtures in tests.
- Keep 42 API access read-only and document any endpoint or classification assumption.
- Report vulnerabilities through GitHub's private vulnerability reporting, not a public issue.

## Code expectations

- Backend changes should include pytest coverage where practical.
- Frontend behavior changes should include Vitest/Testing Library coverage.
- Preserve evidence-aware classifications: unavailable API data must not be treated as proof that a student has no team.
- Keep credentials server-side and avoid introducing browser access to the 42 client secret.
