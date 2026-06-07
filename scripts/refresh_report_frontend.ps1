$ErrorActionPreference = 'Stop'
$PSStyle.OutputRendering = 'PlainText'

<#
Refresh vpnsci-sustech report frontend artifacts.

Repo-maintainer only. This is a source-repo maintenance helper, not a product
CLI feature and not an MCP tool.

What it refreshes:
1. React/TS frontend build output under:
   tools/paper-search-pro/assets/webartifacts_app/paper-report/dist
2. Repo bundle artifact:
   tools/paper-search-pro/assets/webartifacts_app/paper-report/bundle.html
3. User-local bundled runtime copy via:
   uv run python -m vpnsci_sustech.cli report-tools install --force

What it does NOT do:
- does not regenerate any specific report.html
- does not validate visible DOM
- does not restart any long-lived MCP / host process

After this script:
1. regenerate a representative report
2. verify the visible DOM / wording
3. restart long-lived MCP / host processes if they are still serving stale code
#>

$RepoRoot = Split-Path -Parent $PSScriptRoot
$FrontendRoot = Join-Path $RepoRoot 'tools\paper-search-pro\assets\webartifacts_app\paper-report'
$TempRoot = 'F:\AI playground\TempFiles'
$TempIndex = Join-Path $TempRoot 'paper-report-inline-index.html'
$BundlePath = Join-Path $FrontendRoot 'bundle.html'
$InlineCmd = Join-Path $FrontendRoot 'node_modules\.bin\html-inline.cmd'

if (-not (Test-Path -LiteralPath $FrontendRoot)) {
    throw "Frontend root not found: $FrontendRoot"
}

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'pyproject.toml'))) {
    throw "Repo root does not look like the current uv project: $RepoRoot"
}

New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null

Write-Host '[1/4] Build frontend dist assets'
Push-Location $FrontendRoot
try {
    & npm run build

    if (-not (Test-Path -LiteralPath 'dist\index.html')) {
        throw "dist/index.html not found after build."
    }

    if (-not (Test-Path -LiteralPath $InlineCmd)) {
        throw "html-inline command not found: $InlineCmd"
    }

    Write-Host '[2/4] Re-inline dist/index.html into bundle.html'
    $content = Get-Content 'dist\index.html' -Raw -Encoding utf8
    $content = $content -replace '/assets/', './assets/'
    Set-Content -LiteralPath $TempIndex -Value $content -Encoding utf8
    & $InlineCmd -i $TempIndex -o 'bundle.html' -b 'dist'

    if (-not (Test-Path -LiteralPath $BundlePath)) {
        throw "bundle.html was not generated: $BundlePath"
    }
}
finally {
    Pop-Location
}

Write-Host '[3/4] Refresh local bundled runtime copy'
Push-Location $RepoRoot
try {
    & uv run python -m vpnsci_sustech.cli report-tools install --force
}
finally {
    Pop-Location
}

Write-Host '[4/4] Next steps'
Write-Host 'Artifacts refreshed successfully.'
Write-Host 'Next:'
Write-Host '  1. Regenerate a representative report.html'
Write-Host '  2. Verify the visible DOM / wording'
Write-Host '  3. Restart long-lived MCP / host processes if they still serve stale code'
