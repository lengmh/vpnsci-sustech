# paper-search-pro Upstream Snapshot

- Upstream: https://github.com/O0000-code/paper-search-pro
- Snapshot commit: `8b576efd32e9ee786399695267cd9c09302317bf`
- Snapshot date: 2026-05-28
- Upstream license: Apache-2.0 (`tools/paper-search-pro/LICENSE.txt`)
- Notices: `tools/paper-search-pro/NOTICE.md`, `tools/paper-search-pro/THIRD_PARTY.md`

## Purpose

This directory is a vendored snapshot used as the default professional-research report tool for `vpnsci-sustech`.

## Local runtime copy

`vpnsci-sustech` does not execute this snapshot in place. The installer copies it to:

```text
~/.vpnsci-sustech/tools/paper-search-pro
```

The MCP report bridge uses the local runtime copy so generated reports, caches, and user-specific config never pollute the source repository.

## Update policy

To update this snapshot:

1. Fetch upstream into a temporary directory.
2. Verify license/notices still allow redistribution.
3. Replace `tools/paper-search-pro` with the new snapshot.
4. Update this file with the new commit and date.
5. Run the report tool install and smoke tests.

Do not store API keys or generated reports under `tools/paper-search-pro`.
