# Contributing

## Branch naming

```
feature/<short-description>     new functionality
fix/<short-description>         bug fix
docs/<short-description>        documentation only
chore/<short-description>       tooling, config, cleanup
```

Examples: `feature/collection-search`, `fix/booking-capacity`, `docs/personas`

## Workflow

1. `git checkout dev && git pull` — always start from up-to-date dev
2. `git checkout -b feature/your-thing`
3. Commit small and often. Message format: `area: what changed`
   - `backend: add role permission dependency`
   - `frontend: build collection search page`
4. `git push -u origin feature/your-thing`
5. Open a pull request on GitHub, fill in the template
6. Request one reviewer. Merge only after approval and green CI.
7. Delete the branch after merge.

## Rules

- **Never** commit directly to `main` — it is protected.
- **Never** force-push a shared branch.
- **Never** commit `.env` or real credentials.
- Keep branches short-lived. If yours is more than three days old, rebase or merge dev into it.
- Business rules go in `backend/app/services/`, not in route handlers.
- Database models (`models/`) stay separate from API schemas (`schemas/`).

## Before opening a pull request

- [ ] Backend tests pass: `cd backend && pytest tests` (with `TEST_DATABASE_URL` for the integration suite)
- [ ] Front end: `npm run lint && npm test && npm run build` in `frontend/`
- [ ] No secrets in the diff
- [ ] Documentation updated if behaviour changed
