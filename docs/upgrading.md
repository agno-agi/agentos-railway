# Upgrade an existing deployment

This version replaces the old template-owned manager and workflows with Agno's
OS Manager and Company. Saved database records are kept when you upgrade.

## Shared notes database migration

When upgrading from Agno 3.0.x, the filesystem table used by shared notes may
still have the old schema. Agno 3.1 requires `(namespace, user_id, path)` as its
key and refuses the old schema with `SchemaOutdatedError`. It does not migrate
this table automatically.

Back up the database and stop the API before upgrading an existing filesystem
table. Follow the [Agno 3.1 migration instructions](https://github.com/agno-agi/agno/releases/tag/v3.1.0)
and use the [PostgreSQL filesystem migration](https://github.com/agno-agi/agno/blob/v3.1.10/libs/agno/migrations/migrate_filesystem_postgres.py)
against the correct database. Test the migration on a database copy first.
New databases use the new schema automatically.

## Company permissions in Agno 3.1.10

Company records are shared. Write permissions now depend on the caller's scopes,
not on who created the record. For example, a member with `products:delete` can
archive any Product, and a member with `wiki:write` can edit Company wiki pages.
If your deployment relied on creator-only edits, review the scopes you grant
before upgrading. See the [permission change](https://github.com/agno-agi/agno/pull/11270).

Task run sessions keep their existing ownership checks. Manually triggering a
Routine with automatic acceptance still requires the user who authorized that acceptance.

## Upgrade from an older template

Before deploying:

- Disable old `deployment-check` and `run-evals` schedules, whose workflows have been removed.
- Disable or update schedules that use `company-analyst`, including Release intake,
  Daily refresh, Weekly summary, and Weekly review.
- Check saved Studio components for references to removed functions, tools, or knowledge
  bases. Restore what they need or update them before use. Existing product knowledge is kept.
- Check the AgentOS Product's saved settings, owner, Sources, and maintenance schedule.
  Its ID is still `this-agentos`. Code declarations do not overwrite saved edits.
- Remove `ENABLE_MAINTENANCE`, `SANDBOX_ENABLED`, `SANDBOX_IMAGE`, and `SANDBOX_RUNTIME_ARN`
  from env files. Select a sandbox in [app/sandbox.py](../app/sandbox.py); return `None` to turn it off.

Keep historical conversations, notes, and Company work. Update old references rather
than deleting the data they belong to.

If you changed repositories, check the AgentOS Product's saved Sources and remove
any outdated template URL. Setting `REPOSITORY` in `app/sandbox.py` adds a Git Source
for that URL; it doesn't remove previously saved Sources. Keep the local Source
so Company can read the code. Sandbox Company Tasks also need the saved Git Source
to match the configured repository. See the [sandbox guide](sandboxes.md#company-tasks).

Return to the [deployment instructions](../README.md#deploy-in-production).
