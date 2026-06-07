# paper-report frontend

React + TypeScript + Vite source for the single-file report frontend used by
`html_renderer_webartifacts.py`.

## Maintainer boundary

This directory is **source** for the report frontend, not the final runtime
artifact by itself.

There are multiple layers that can drift:

1. `src/**` source
2. `dist/assets/*` build output
3. repo `bundle.html`
4. user-local runtime copy under:

   ```text
   ~/.vpnsci-sustech/tools/paper-search-pro/assets/webartifacts_app/paper-report/bundle.html
   ```

If you only run `npm run build`, you refresh layer 2 but **not** layer 3/4.

## Recommended refresh shortcut

From the repo root:

```powershell
pwsh -File scripts/refresh_report_frontend.ps1
```

This repo-maintainer script will:

1. run `npm run build`
2. inline `dist/index.html` back into repo `bundle.html`
3. run `uv run python -m vpnsci_sustech.cli report-tools install --force`

It does **not** regenerate a report or validate the DOM. After running it,
regenerate a representative `report.html` and verify the visible page.

## Manual refresh steps

If you need the explicit manual chain instead of the shortcut script:

```powershell
cd tools/paper-search-pro/assets/webartifacts_app/paper-report
npm run build

$tmp = 'F:\AI playground\TempFiles\paper-report-inline-index.html'
((Get-Content 'dist/index.html' -Raw -Encoding utf8) -replace '/assets/', './assets/') |
  Set-Content -LiteralPath $tmp -Encoding utf8
.\node_modules\.bin\html-inline.cmd -i $tmp -o 'bundle.html' -b 'dist'

cd ../../../../..
uv run python -m vpnsci_sustech.cli report-tools install --force
```

## Notes

- This is a repo maintenance workflow, not a packaged end-user feature.
- If a long-lived MCP/host process still serves stale output after refresh, it
  may need a restart.
