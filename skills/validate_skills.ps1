param(
  [switch]$SkipPython,
  [switch]$SkipNode
)

$ErrorActionPreference = 'Stop'

function Add-Problem {
  param(
    [System.Collections.Generic.List[string]]$Problems,
    [string]$Message
  )
  $Problems.Add($Message) | Out-Null
}

function Write-Section {
  param([string]$Title)
  Write-Host ''
  Write-Host $Title -ForegroundColor Cyan
}

function Test-Command {
  param([string]$Name)
  return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$skillsRoot = Join-Path $repoRoot 'skills'
$problems = New-Object 'System.Collections.Generic.List[string]'

Write-Section 'Validating skills folder structure'
if (-not (Test-Path (Join-Path $skillsRoot 'README.md'))) {
  Add-Problem -Problems $problems -Message 'Missing skills/README.md'
}

$skillDirs = Get-ChildItem -Path $skillsRoot -Directory | Where-Object { $_.Name -ne '.git' }
if ($skillDirs.Count -eq 0) {
  Add-Problem -Problems $problems -Message 'No skill directories found under skills/'
}

foreach ($dir in $skillDirs) {
  $skillMd = Join-Path $dir.FullName 'SKILL.md'
  if (-not (Test-Path $skillMd)) {
    Add-Problem -Problems $problems -Message ("Missing SKILL.md: {0}" -f $dir.FullName)
    continue
  }

  $content = Get-Content -Path $skillMd -Raw
  if ($content -notmatch "(?s)^(\uFEFF)?---\s*.*?\s*---\s*") {
    Add-Problem -Problems $problems -Message ("Missing YAML frontmatter in {0}" -f $skillMd)
  } else {
    if ($content -notmatch "(?m)^name:\s*\S+") {
      Add-Problem -Problems $problems -Message ("Frontmatter missing `name` in {0}" -f $skillMd)
    }
    if ($content -notmatch "(?m)^description:\s*\S+") {
      Add-Problem -Problems $problems -Message ("Frontmatter missing `description` in {0}" -f $skillMd)
    }
  }

  $codeSpans = [regex]::Matches($content, '`([^`]+)`')
  foreach ($span in $codeSpans) {
    $raw = $span.Groups[1].Value.Trim()
    if ($raw -notmatch '^skills[\\/]') { continue }
    if ($raw -notmatch '\.(ps1|py|js|html|md)$') { continue }
    $relative = $raw.Replace('/', '\')
    $fullPath = Join-Path $repoRoot $relative
    if (-not (Test-Path $fullPath)) {
      Add-Problem -Problems $problems -Message ("Broken path reference in {0}: {1}" -f $skillMd, $raw)
    }
  }
}

Write-Section 'Checking PowerShell script parse'
$ps1Files = Get-ChildItem -Path $skillsRoot -Recurse -File -Filter *.ps1
foreach ($file in $ps1Files) {
  $tokens = $null
  $errors = $null
  [System.Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$errors) | Out-Null
  if ($errors -and $errors.Count -gt 0) {
    $detail = ($errors | ForEach-Object { $_.Message }) -join ' | '
    Add-Problem -Problems $problems -Message ("PowerShell parse error in {0}: {1}" -f $file.FullName, $detail)
  }
}

if (-not $SkipPython) {
  Write-Section 'Checking Python script compilation'
  if (-not (Test-Command -Name 'python')) {
    Add-Problem -Problems $problems -Message 'python not found on PATH'
  } else {
    $pyFiles = Get-ChildItem -Path $skillsRoot -Recurse -File -Filter *.py
    foreach ($file in $pyFiles) {
      try {
        & python -m py_compile $file.FullName | Out-Null
      } catch {
        Add-Problem -Problems $problems -Message ("Python compile error in {0}: {1}" -f $file.FullName, $_.Exception.Message)
      }
    }
  }
}

if (-not $SkipNode) {
  Write-Section 'Checking Node.js script syntax'
  if (-not (Test-Command -Name 'node')) {
    Add-Problem -Problems $problems -Message 'node not found on PATH'
  } else {
    $jsFiles = Get-ChildItem -Path $skillsRoot -Recurse -File -Filter *.js
    foreach ($file in $jsFiles) {
      $result = & node --check $file.FullName 2>&1
      if ($LASTEXITCODE -ne 0) {
        Add-Problem -Problems $problems -Message ("Node syntax error in {0}: {1}" -f $file.FullName, ($result -join ' '))
      }
    }
  }
}

Write-Section 'Checking HTML templates'
$htmlFiles = Get-ChildItem -Path $skillsRoot -Recurse -File -Filter *.html
foreach ($file in $htmlFiles) {
  $html = Get-Content -Path $file.FullName -Raw
  foreach ($token in '{{TITLE}}','{{SUBTITLE}}','{{CARDS}}') {
    if ($html -notmatch [regex]::Escape($token)) {
      Add-Problem -Problems $problems -Message ("Missing template token {0} in {1}" -f $token, $file.FullName)
    }
  }
}

Write-Host ''
if ($problems.Count -gt 0) {
  Write-Host ("FAILED ({0} issues):" -f $problems.Count) -ForegroundColor Red
  foreach ($p in $problems) { Write-Host ("- {0}" -f $p) -ForegroundColor Red }
  exit 1
}

Write-Host 'OK: skills validation passed.' -ForegroundColor Green
exit 0
