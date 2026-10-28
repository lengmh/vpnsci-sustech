$ErrorActionPreference = 'Stop'
$SourceScript = Join-Path $PSScriptRoot '..\scripts\refresh_report_frontend.ps1'
$Scratch = Join-Path ([System.IO.Path]::GetTempPath()) ("vpnsci-refresh-test-{0}" -f [guid]::NewGuid().ToString('N'))
$OldCapture = $env:VPNSCI_INLINE_CAPTURE
try {
    $Project = Join-Path $Scratch 'fixture project'
    $Frontend = Join-Path $Project 'tools\paper-search-pro\assets\webartifacts_app\paper-report'
    New-Item -ItemType Directory -Force -Path (Join-Path $Project 'scripts') | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $Frontend 'dist') | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $Frontend 'node_modules\.bin') | Out-Null
    $Script = Join-Path $Project 'scripts\refresh_report_frontend.ps1'
    Copy-Item -LiteralPath $SourceScript -Destination $Script
    Set-Content -LiteralPath (Join-Path $Project 'pyproject.toml') -Value '[project]' -Encoding utf8
    $Inline = Join-Path $Frontend 'node_modules\.bin\html-inline.cmd'
    @'
param([string]$InputPath)
[System.IO.File]::WriteAllText($env:VPNSCI_INLINE_CAPTURE, $InputPath)
'@ | Set-Content -LiteralPath (Join-Path (Split-Path -Parent $Inline) 'capture.ps1') -Encoding utf8
    @'
@echo off
pwsh -NoProfile -File "%~dp0capture.ps1" "%~2"
copy /y "%~2" "%~4" >nul
'@ | Set-Content -LiteralPath $Inline -Encoding ascii
    $env:VPNSCI_INLINE_CAPTURE = Join-Path $Scratch 'capture.txt'
    function global:npm {
        Set-Content -LiteralPath 'dist\index.html' -Value '<html>/assets/example.js</html>' -Encoding utf8
    }
    function global:uv {
        if (($args -join ' ') -ne 'run python -m vpnsci_sustech.cli report-tools install --force') {
            throw 'Unexpected runtime refresh command'
        }
    }

    & $Script
    $DefaultInput = (Get-Content -LiteralPath $env:VPNSCI_INLINE_CAPTURE -Raw).Trim()
    if ((Split-Path -Parent $DefaultInput) -ne ([System.IO.Path]::GetTempPath()).TrimEnd('\', '/')) {
        throw 'Default inline file was not created under the system temporary directory'
    }
    if (Test-Path -LiteralPath $DefaultInput) { throw 'Default inline file was not cleaned up' }

    $ExplicitRoot = Join-Path $Scratch '测试 workspace'
    New-Item -ItemType Directory -Path $ExplicitRoot | Out-Null
    $Keep = Join-Path $ExplicitRoot 'paper-report-inline-index.html'
    Set-Content -LiteralPath $Keep -Value 'keep' -Encoding utf8
    & $Script -TempRoot $ExplicitRoot
    $ExplicitInput = (Get-Content -LiteralPath $env:VPNSCI_INLINE_CAPTURE -Raw).Trim()
    if ((Split-Path -Parent $ExplicitInput) -ne $ExplicitRoot) { throw 'Explicit TempRoot was ignored' }
    if ($ExplicitInput -eq $DefaultInput) { throw 'Inline filename was reused' }
    if (Test-Path -LiteralPath $ExplicitInput) { throw 'Explicit inline file was not cleaned up' }
    if ((Get-Content -LiteralPath $Keep -Raw).Trim() -ne 'keep') { throw 'An unrelated file was modified' }
    if ((Get-Content -LiteralPath (Join-Path $Frontend 'bundle.html') -Raw) -notmatch '\./assets/example.js') {
        throw 'Inlining input did not retain the existing asset rewrite'
    }

    Push-Location $Project
    try { & $Script -TempRoot '.\relative 测试' }
    finally { Pop-Location }
    $RelativeInput = (Get-Content -LiteralPath $env:VPNSCI_INLINE_CAPTURE -Raw).Trim()
    if ((Split-Path -Parent $RelativeInput) -ne (Join-Path $Project 'relative 测试')) {
        throw 'Relative TempRoot was resolved against the wrong working directory'
    }
    if (Test-Path -LiteralPath $RelativeInput) { throw 'Relative inline file was not cleaned up' }

    Remove-Item -LiteralPath (Join-Path $Frontend 'bundle.html')
    @'
@echo off
pwsh -NoProfile -File "%~dp0capture.ps1" "%~2"
exit /b 1
'@ | Set-Content -LiteralPath $Inline -Encoding ascii
    $Failed = $false
    try { & $Script -TempRoot $ExplicitRoot }
    catch { $Failed = $true }
    if (-not $Failed) { throw 'Missing bundle failure was not reported' }
    $FailedInput = (Get-Content -LiteralPath $env:VPNSCI_INLINE_CAPTURE -Raw).Trim()
    if (Test-Path -LiteralPath $FailedInput) { throw 'Inline file survived a failed build' }
    if (-not (Test-Path -LiteralPath $Keep)) { throw 'Failure cleanup removed an unrelated file' }
    Write-Host 'Frontend temporary path, override, success/failure cleanup checks passed.'
    $global:LASTEXITCODE = 0
}
finally {
    $env:VPNSCI_INLINE_CAPTURE = $OldCapture
    Remove-Item Function:\npm -ErrorAction SilentlyContinue
    Remove-Item Function:\uv -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $Scratch) { Remove-Item -LiteralPath $Scratch -Recurse -Force }
}
