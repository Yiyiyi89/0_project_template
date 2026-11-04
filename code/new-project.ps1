param(
    [Parameter(Mandatory = $true)]
    [string]$Destination
)
$ErrorActionPreference = 'Stop'
$templateRoot = Split-Path -Parent $PSScriptRoot
$targetPath = [System.IO.Path]::GetFullPath($Destination)
if (Test-Path -LiteralPath $targetPath) {
    if (-not (Test-Path -LiteralPath $targetPath -PathType Container)) {
        throw 'Destination must be a directory.'
    }
    if (Get-ChildItem -LiteralPath $targetPath -Force | Select-Object -First 1) {
        throw 'Destination must be empty. No existing files were changed.'
    }
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Install Git before initializing a project.'
}
# Build an explicit file list. Never copy repository metadata or project data.
$files = @('README.md', 'README.py', 'AGENTS.md', 'DECISIONS.md', '.gitignore', 'requirements.txt')
foreach ($folder in @('code')) {
    $base = Join-Path $templateRoot $folder
    $files += Get-ChildItem -LiteralPath $base -File -Recurse -Force |
        Where-Object {
            $relative = $_.FullName.Substring($templateRoot.Length + 1)
            $relative -notmatch '(^|[\\/])(\.git|\.venv|__pycache__)([\\/]|$)' -and
            $_.Extension -in @('.py', '.do', '.md', '.ps1') -and
            -not $_.LinkType
        } | ForEach-Object { $_.FullName.Substring($templateRoot.Length + 1) }
}
New-Item -ItemType Directory -Path $targetPath -Force | Out-Null
foreach ($relative in $files) {
    $targetFile = Join-Path $targetPath $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $targetFile) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $templateRoot $relative) -Destination $targetFile
}
foreach ($folder in @('data/input', 'data/temp', 'data/output', 'data/tables_and_figures', 'resources', 'trial')) {
    $directory = Join-Path $targetPath $folder
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    New-Item -ItemType File -Path (Join-Path $directory '.gitkeep') | Out-Null
}
git -C $targetPath init -b main
if ($LASTEXITCODE -ne 0) { throw 'Files copied, but Git initialization failed. Inspect the destination.' }
Write-Output "Project created at $targetPath. Review it, then stage and commit when ready."
