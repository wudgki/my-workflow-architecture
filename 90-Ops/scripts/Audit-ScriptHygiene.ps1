#Requires -Version 5.1
<#
.SYNOPSIS
    Audit PowerShell scripts (and other text files) for encoding hazards
    that break Windows PowerShell 5.1 parsing.

.DESCRIPTION
    Detects:
      1. UTF-8 BOM presence (warning for .ps1: PS 5.1 needs BOM if file
         contains non-ASCII; absence triggers ANSI mojibake)
      2. Hidden / zero-width / bidi / control Unicode characters anywhere
      3. ASCII look-alikes: smart quotes, en/em dash, ellipsis, NBSP
      4. Non-ASCII characters inside the CODE region of .ps1 files
         (after stripping block comments, line comments, "double" / 'single'
         strings, and @ here-strings)
      5. Mixed CRLF / LF line endings within a single file
      6. Optional: trailing whitespace per line

    Exit code:
      0 = all files passed (zero critical findings)
      1 = at least one file failed any critical check
      2 = invalid arguments / I/O failure

    Tested on Windows PowerShell 5.1 and PowerShell 7.x.

.PARAMETER Path
    Root directory to scan, or a single file. Default: current directory.

.PARAMETER Recurse
    Recurse into subdirectories. Default: true.

.PARAMETER Include
    Filename glob patterns to scan. Default: *.ps1, *.psm1, *.psd1
    For broader audits, pass e.g. -Include '*.ps1','*.psm1','*.yaml','*.md'

.PARAMETER ExcludePath
    Path patterns to exclude (matched against full path). Default excludes
    .git, node_modules, dist, build, __pycache__.

.PARAMETER Strict
    Treat warnings as errors. CI mode. Default: false.

.PARAMETER CheckTrailingWhitespace
    Also report lines with trailing whitespace. Cosmetic only, off by default.

.PARAMETER Format
    Output format: text (default, colorful), summary (one line per file),
    json (machine-readable, prints to stdout, no decoration).

.PARAMETER FailOn
    Severity threshold that causes non-zero exit. One of: critical (default),
    warning, none. Use 'none' to always exit 0 regardless of findings.

.EXAMPLE
    # Audit every .ps1 in the current repo
    .\Audit-ScriptHygiene.ps1

.EXAMPLE
    # Audit a single file with full detail
    .\Audit-ScriptHygiene.ps1 -Path .\90-Ops\scripts\Init-AIWorkspace.ps1

.EXAMPLE
    # Audit broader file types in a release branch
    .\Audit-ScriptHygiene.ps1 -Path . -Include '*.ps1','*.yaml','*.md'

.EXAMPLE
    # CI mode: any warning fails the build
    .\Audit-ScriptHygiene.ps1 -Strict -Format summary

.EXAMPLE
    # Machine-readable output piped to a tool
    .\Audit-ScriptHygiene.ps1 -Format json | ConvertFrom-Json

.NOTES
    Author: Samuel Wu workflow blueprint
    Requires: PowerShell 5.1+ or PowerShell 7
    Self-test: this file MUST itself pass the audit (pure ASCII).
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false, Position = 0)]
    [string]$Path = '.',

    [Parameter(Mandatory = $false)]
    [bool]$Recurse = $true,

    [Parameter(Mandatory = $false)]
    [string[]]$Include = @('*.ps1', '*.psm1', '*.psd1'),

    [Parameter(Mandatory = $false)]
    [string[]]$ExcludePath = @('\.git\', '\node_modules\', '\dist\', '\build\', '\__pycache__\'),

    [Parameter(Mandatory = $false)]
    [switch]$Strict,

    [Parameter(Mandatory = $false)]
    [switch]$CheckTrailingWhitespace,

    [Parameter(Mandatory = $false)]
    [ValidateSet('text', 'summary', 'json')]
    [string]$Format = 'text',

    [Parameter(Mandatory = $false)]
    [ValidateSet('critical', 'warning', 'none')]
    [string]$FailOn = 'critical'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# ============================================================
# Codepoint classifier
# ============================================================

# Returns a tag string if the codepoint is suspicious, else $null.
function Get-CodepointHazardTag {
    param([int]$Cp)

    # BOM / Zero-width no-break space
    if ($Cp -eq 0xFEFF) { return 'BOM_ZWNBSP' }

    # Zero-width spaces / joiners / LRM / RLM (U+200B..U+200F)
    if ($Cp -ge 0x200B -and $Cp -le 0x200F) { return 'ZERO_WIDTH' }

    # Line / paragraph separator (rendered invisibly in some editors)
    if ($Cp -eq 0x2028 -or $Cp -eq 0x2029) { return 'LINE_SEP' }

    # Bidi overrides (LRE/RLE/PDF/LRO/RLO) - the Trojan Source family
    if ($Cp -ge 0x202A -and $Cp -le 0x202E) { return 'BIDI_OVERRIDE' }

    # Word joiner / invisible operators
    if ($Cp -ge 0x2060 -and $Cp -le 0x2064) { return 'WORD_JOINER' }

    # Bidi isolates LRI/RLI/FSI/PDI - also Trojan Source family
    if ($Cp -ge 0x2066 -and $Cp -le 0x2069) { return 'BIDI_ISOLATE' }

    # NBSP / narrow NBSP / OGHAM / medium math / ideographic / mongolian
    if ($Cp -eq 0x00A0)                       { return 'NBSP' }
    if ($Cp -eq 0x202F)                       { return 'NARROW_NBSP' }
    if ($Cp -eq 0x1680)                       { return 'OGHAM_SPACE' }
    if ($Cp -ge 0x2000 -and $Cp -le 0x200A)   { return 'UNUSUAL_SPACE' }
    if ($Cp -eq 0x205F)                       { return 'MEDIUM_MATH_SPACE' }
    if ($Cp -eq 0x3000)                       { return 'IDEOGRAPHIC_SPACE' }
    if ($Cp -eq 0x180E)                       { return 'MONGOL_VOWEL_SEP' }

    # Soft hyphen
    if ($Cp -eq 0x00AD)                       { return 'SOFT_HYPHEN' }

    # Smart quotes / dashes / ellipsis - look like ASCII but break parsers
    if ($Cp -eq 0x2018 -or $Cp -eq 0x2019)    { return 'SMART_QUOTE_SINGLE' }
    if ($Cp -eq 0x201C -or $Cp -eq 0x201D)    { return 'SMART_QUOTE_DOUBLE' }
    if ($Cp -eq 0x2013)                       { return 'EN_DASH' }
    if ($Cp -eq 0x2014)                       { return 'EM_DASH' }
    if ($Cp -eq 0x2026)                       { return 'ELLIPSIS' }

    # C0 / C1 control characters (excluding tab / LF / CR)
    if ($Cp -le 0x08 -or $Cp -eq 0x0B -or `
        ($Cp -ge 0x0E -and $Cp -le 0x1F) -or `
        ($Cp -ge 0x7F -and $Cp -le 0x9F)) {
        if ($Cp -ne 0x09 -and $Cp -ne 0x0A -and $Cp -ne 0x0D) {
            return 'CONTROL_CHAR'
        }
    }

    return $null
}

# Severity per tag. CRITICAL = breaks parsing or hides malicious code.
function Get-HazardSeverity {
    param([string]$Tag)
    switch ($Tag) {
        'BIDI_OVERRIDE'      { 'CRITICAL'; break }
        'BIDI_ISOLATE'       { 'CRITICAL'; break }
        'CONTROL_CHAR'       { 'CRITICAL'; break }
        'ZERO_WIDTH'         { 'CRITICAL'; break }
        'WORD_JOINER'        { 'CRITICAL'; break }
        'LINE_SEP'           { 'CRITICAL'; break }
        'BOM_ZWNBSP'         { 'CRITICAL'; break }
        'SMART_QUOTE_SINGLE' { 'CRITICAL'; break }
        'SMART_QUOTE_DOUBLE' { 'CRITICAL'; break }
        'EN_DASH'            { 'CRITICAL'; break }
        'EM_DASH'            { 'CRITICAL'; break }
        'NBSP'               { 'CRITICAL'; break }
        'NARROW_NBSP'        { 'WARNING';  break }
        'OGHAM_SPACE'        { 'WARNING';  break }
        'UNUSUAL_SPACE'      { 'WARNING';  break }
        'MEDIUM_MATH_SPACE'  { 'WARNING';  break }
        'IDEOGRAPHIC_SPACE'  { 'WARNING';  break }
        'MONGOL_VOWEL_SEP'   { 'WARNING';  break }
        'SOFT_HYPHEN'        { 'WARNING';  break }
        'ELLIPSIS'           { 'WARNING';  break }
        default              { 'INFO' }
    }
}

# ============================================================
# Code-region scanner for .ps1 files
# ============================================================

# Walk source character-by-character, tagging each char's zone:
#   code | bc (block comment) | lc (line comment)
#   sd (string "...") | ss (string '...')
#   hd (here-string @"..."@) | hs (here-string @'...'@)
function Get-PowerShellZoneMap {
    param([string]$Source)

    $n = $Source.Length
    $zones = New-Object 'string[]' $n
    $state = 'code'
    $i = 0
    while ($i -lt $n) {
        $c = $Source[$i]
        $nxt = if ($i + 1 -lt $n) { $Source[$i + 1] } else { [char]0 }

        switch ($state) {
            'code' {
                # Block comment <# ... #>
                if ($c -eq '<' -and $nxt -eq '#') {
                    $zones[$i] = 'bc'; $zones[$i + 1] = 'bc'
                    $state = 'bc'; $i += 2; continue
                }
                # Here-strings start at @" or @'
                if ($c -eq '@' -and $nxt -eq '"') {
                    $zones[$i] = 'hd'; $zones[$i + 1] = 'hd'
                    $state = 'hd'; $i += 2; continue
                }
                if ($c -eq '@' -and $nxt -eq "'") {
                    $zones[$i] = 'hs'; $zones[$i + 1] = 'hs'
                    $state = 'hs'; $i += 2; continue
                }
                # Line comment
                if ($c -eq '#') {
                    $zones[$i] = 'lc'
                    $state = 'lc'; $i++; continue
                }
                # Strings
                if ($c -eq '"') {
                    $zones[$i] = 'sd'
                    $state = 'sd'; $i++; continue
                }
                if ($c -eq "'") {
                    $zones[$i] = 'ss'
                    $state = 'ss'; $i++; continue
                }
                $zones[$i] = 'code'
                $i++
            }
            'bc' {
                $zones[$i] = 'bc'
                if ($c -eq '#' -and $nxt -eq '>') {
                    $zones[$i + 1] = 'bc'
                    $state = 'code'; $i += 2; continue
                }
                $i++
            }
            'lc' {
                $zones[$i] = 'lc'
                if ($c -eq "`n") { $state = 'code' }
                $i++
            }
            'sd' {
                $zones[$i] = 'sd'
                if ($c -eq '"') { $state = 'code' }
                elseif ($c -eq "`n") { $state = 'code' }   # tolerate broken multi-line
                $i++
            }
            'ss' {
                $zones[$i] = 'ss'
                if ($c -eq "'") { $state = 'code' }
                elseif ($c -eq "`n") { $state = 'code' }
                $i++
            }
            'hd' {
                $zones[$i] = 'hd'
                if ($c -eq '"' -and $nxt -eq '@') {
                    $zones[$i + 1] = 'hd'
                    $state = 'code'; $i += 2; continue
                }
                $i++
            }
            'hs' {
                $zones[$i] = 'hs'
                if ($c -eq "'" -and $nxt -eq '@') {
                    $zones[$i + 1] = 'hs'
                    $state = 'code'; $i += 2; continue
                }
                $i++
            }
        }
    }
    return $zones
}

# ============================================================
# Per-file audit
# ============================================================

function Invoke-FileAudit {
    param(
        [string]$FilePath,
        [bool]$IsPowerShell,
        [bool]$AlsoCheckTrailingWS
    )

    $result = [pscustomobject]@{
        Path             = $FilePath
        Size             = 0
        HasBom           = $false
        IsPowerShell     = $IsPowerShell
        Findings         = @()  # list of finding objects
        CriticalCount    = 0
        WarningCount     = 0
        InfoCount        = 0
        ReadError        = $null
    }

    try {
        $raw = [System.IO.File]::ReadAllBytes($FilePath)
    } catch {
        $result.ReadError = $_.Exception.Message
        return $result
    }
    $result.Size = $raw.Length

    # BOM detection
    $hasBom = $false
    if ($raw.Length -ge 3 -and $raw[0] -eq 0xEF -and $raw[1] -eq 0xBB -and $raw[2] -eq 0xBF) {
        $hasBom = $true
    }
    $result.HasBom = $hasBom

    # Decode (utf-8-sig handling: skip BOM bytes if present)
    try {
        if ($hasBom) {
            $text = [System.Text.Encoding]::UTF8.GetString($raw, 3, $raw.Length - 3)
        } else {
            # Validate UTF-8 strictly
            $strictUtf8 = New-Object System.Text.UTF8Encoding($false, $true)
            $text = $strictUtf8.GetString($raw)
        }
    } catch {
        $result.Findings += [pscustomobject]@{
            Severity = 'CRITICAL'
            Code     = 'INVALID_UTF8'
            Line     = 0
            Column   = 0
            Detail   = 'File is not valid UTF-8: ' + $_.Exception.Message
        }
        $result.CriticalCount++
        return $result
    }

    # BOM advisory for .ps1: Windows PS 5.1 reads no-BOM files as ANSI;
    # if file is pure ASCII, no-BOM is fine. If file has non-ASCII and
    # also has no BOM, that is a clear hazard for PS 5.1.
    # We'll surface an INFO if .ps1 has BOM (unusual but valid),
    # and CRITICAL if .ps1 has non-ASCII without BOM.
    $hasNonAscii = $false
    foreach ($ch in $text.ToCharArray()) {
        if ([int]$ch -gt 127) { $hasNonAscii = $true; break }
    }
    if ($IsPowerShell) {
        if ($hasBom) {
            $result.Findings += [pscustomobject]@{
                Severity = 'INFO'
                Code     = 'PS_HAS_BOM'
                Line     = 1
                Column   = 1
                Detail   = '.ps1 has UTF-8 BOM. OK for PS 5.1, harmless for PS 7.'
            }
            $result.InfoCount++
        }
        if ((-not $hasBom) -and $hasNonAscii) {
            $result.Findings += [pscustomobject]@{
                Severity = 'CRITICAL'
                Code     = 'PS_NONASCII_NO_BOM'
                Line     = 1
                Column   = 1
                Detail   = '.ps1 contains non-ASCII characters but has no UTF-8 BOM. Windows PowerShell 5.1 will read this as ANSI and produce mojibake or parser errors. Either rewrite as pure ASCII (recommended) or save with UTF-8 BOM.'
            }
            $result.CriticalCount++
        }
    }

    # Build line index for fast line/column lookup
    $lineStarts = New-Object 'System.Collections.Generic.List[int]'
    $lineStarts.Add(0)
    for ($i = 0; $i -lt $text.Length; $i++) {
        if ($text[$i] -eq "`n") {
            $lineStarts.Add($i + 1)
        }
    }
    function Resolve-Position {
        param([int]$Idx)
        # Binary search
        $lo = 0; $hi = $lineStarts.Count - 1
        while ($lo -lt $hi) {
            $mid = [int](($lo + $hi + 1) / 2)
            if ($lineStarts[$mid] -le $Idx) { $lo = $mid } else { $hi = $mid - 1 }
        }
        $line = $lo + 1
        $col = $Idx - $lineStarts[$lo] + 1
        return @{ Line = $line; Column = $col }
    }

    # Compute zone map for .ps1
    $zones = $null
    if ($IsPowerShell) {
        $zones = Get-PowerShellZoneMap -Source $text
    }

    # Single pass: find suspicious codepoints
    for ($i = 0; $i -lt $text.Length; $i++) {
        $cp = [int]$text[$i]
        $tag = Get-CodepointHazardTag -Cp $cp
        if ($tag) {
            # Skip the very first BOM character (we already reported it via hasBom logic)
            if ($tag -eq 'BOM_ZWNBSP' -and $i -eq 0 -and $hasBom) { continue }

            $sev = Get-HazardSeverity -Tag $tag
            $pos = Resolve-Position -Idx $i

            # If .ps1 and non-critical char is INSIDE a comment or string,
            # we still report but downgrade severity by one level (it cannot
            # break parsing in those zones, but smart quotes may indicate
            # a typo by an editor).
            if ($IsPowerShell -and $zones -and $i -lt $zones.Length) {
                $z = $zones[$i]
                $inSafeZone = ($z -eq 'bc' -or $z -eq 'lc' -or $z -eq 'sd' -or `
                              $z -eq 'ss' -or $z -eq 'hd' -or $z -eq 'hs')
                # Bidi overrides and control chars are still dangerous
                # ANYWHERE (Trojan Source). Do not downgrade those.
                $alwaysDangerous = ($tag -eq 'BIDI_OVERRIDE' -or $tag -eq 'BIDI_ISOLATE' -or `
                                    $tag -eq 'CONTROL_CHAR' -or $tag -eq 'ZERO_WIDTH' -or `
                                    $tag -eq 'WORD_JOINER' -or $tag -eq 'LINE_SEP')
                if ($inSafeZone -and -not $alwaysDangerous) {
                    if ($sev -eq 'CRITICAL') { $sev = 'WARNING' }
                    elseif ($sev -eq 'WARNING') { $sev = 'INFO' }
                }
            }

            $result.Findings += [pscustomobject]@{
                Severity = $sev
                Code     = $tag
                Line     = $pos.Line
                Column   = $pos.Column
                Detail   = ('Codepoint U+{0:X4} ({1})' -f $cp, $tag)
            }
            switch ($sev) {
                'CRITICAL' { $result.CriticalCount++ }
                'WARNING'  { $result.WarningCount++ }
                'INFO'     { $result.InfoCount++ }
            }
        }
    }

    # Code-region non-ASCII for .ps1 (this is the killer for PS 5.1)
    if ($IsPowerShell -and $zones) {
        for ($i = 0; $i -lt $text.Length; $i++) {
            $cp = [int]$text[$i]
            if ($cp -gt 127 -and $zones[$i] -eq 'code') {
                $pos = Resolve-Position -Idx $i
                $result.Findings += [pscustomobject]@{
                    Severity = 'CRITICAL'
                    Code     = 'CODE_NONASCII'
                    Line     = $pos.Line
                    Column   = $pos.Column
                    Detail   = ('Non-ASCII codepoint U+{0:X4} in CODE region (not inside a string or comment). PS 5.1 will fail to parse this without a BOM.' -f $cp)
                }
                $result.CriticalCount++
            }
        }
    }

    # Mixed line endings
    $crlfCount = 0
    $loneLfCount = 0
    for ($i = 0; $i -lt $raw.Length; $i++) {
        if ($raw[$i] -eq 0x0A) {
            if ($i -gt 0 -and $raw[$i - 1] -eq 0x0D) {
                $crlfCount++
            } else {
                $loneLfCount++
            }
        }
    }
    if ($crlfCount -gt 0 -and $loneLfCount -gt 0) {
        $result.Findings += [pscustomobject]@{
            Severity = 'WARNING'
            Code     = 'MIXED_LINE_ENDINGS'
            Line     = 0
            Column   = 0
            Detail   = "Mixed line endings: CRLF=$crlfCount, lone LF=$loneLfCount"
        }
        $result.WarningCount++
    }

    # Trailing whitespace (optional)
    if ($AlsoCheckTrailingWS) {
        $lineNo = 0
        foreach ($ln in ($text -split "`n")) {
            $lineNo++
            $stripped = $ln.TrimEnd("`r")
            if ($stripped -match '[\t ]+$') {
                $result.Findings += [pscustomobject]@{
                    Severity = 'INFO'
                    Code     = 'TRAILING_WHITESPACE'
                    Line     = $lineNo
                    Column   = $stripped.Length
                    Detail   = 'Trailing whitespace'
                }
                $result.InfoCount++
            }
        }
    }

    return $result
}

# ============================================================
# Discovery
# ============================================================

function Get-FilesToAudit {
    param(
        [string]$Root,
        [bool]$DoRecurse,
        [string[]]$IncludeGlobs,
        [string[]]$ExcludePatterns
    )
    $rootItem = Get-Item -LiteralPath $Root -ErrorAction Stop
    if ($rootItem.PSIsContainer) {
        $params = @{ Path = $rootItem.FullName; Include = $IncludeGlobs; File = $true }
        if ($DoRecurse) { $params.Recurse = $true }
        # Get-ChildItem -Include only works with -Recurse or trailing wildcard,
        # so we always pass -Recurse and filter manually if needed.
        $params.Recurse = $true
        $all = Get-ChildItem @params
        if (-not $DoRecurse) {
            $all = $all | Where-Object { $_.Directory.FullName -eq $rootItem.FullName }
        }
    } else {
        $all = @($rootItem)
    }

    # Apply excludes
    $filtered = foreach ($f in $all) {
        $skip = $false
        foreach ($pat in $ExcludePatterns) {
            if ($f.FullName -like ('*' + $pat + '*')) { $skip = $true; break }
        }
        if (-not $skip) { $f }
    }
    return $filtered
}

# ============================================================
# Reporters
# ============================================================

function Write-FindingText {
    param([object]$Finding)
    $color = switch ($Finding.Severity) {
        'CRITICAL' { 'Red' }
        'WARNING'  { 'Yellow' }
        'INFO'     { 'DarkGray' }
        default    { 'White' }
    }
    $loc = if ($Finding.Line -gt 0) { ('  L{0}:{1}' -f $Finding.Line, $Finding.Column) } else { '' }
    Write-Host ('  [{0,-8}] {1,-22}{2}  {3}' -f $Finding.Severity, $Finding.Code, $loc, $Finding.Detail) -ForegroundColor $color
}

function Write-FileReportText {
    param([object]$FileResult)

    $rel = $FileResult.Path
    if ($FileResult.ReadError) {
        Write-Host ('FAIL  {0}' -f $rel) -ForegroundColor Red
        Write-Host ('  read error: {0}' -f $FileResult.ReadError) -ForegroundColor Red
        return
    }

    $status = if ($FileResult.CriticalCount -gt 0) { 'FAIL' }
              elseif ($FileResult.WarningCount -gt 0) { 'WARN' }
              else { 'PASS' }
    $color = switch ($status) {
        'FAIL' { 'Red' }
        'WARN' { 'Yellow' }
        'PASS' { 'Green' }
    }
    Write-Host ('{0}  {1}  ({2} bytes, BOM={3})' -f `
        $status, $rel, $FileResult.Size, $FileResult.HasBom) -ForegroundColor $color
    foreach ($f in $FileResult.Findings) {
        Write-FindingText -Finding $f
    }
}

function Write-FileReportSummary {
    param([object]$FileResult)
    $status = if ($FileResult.ReadError) { 'ERROR' }
              elseif ($FileResult.CriticalCount -gt 0) { 'FAIL' }
              elseif ($FileResult.WarningCount -gt 0) { 'WARN' }
              else { 'PASS' }
    $color = switch ($status) {
        'ERROR' { 'Red' }
        'FAIL'  { 'Red' }
        'WARN'  { 'Yellow' }
        'PASS'  { 'Green' }
    }
    Write-Host ('{0}  C={1}  W={2}  I={3}  {4}' -f `
        $status, $FileResult.CriticalCount, $FileResult.WarningCount, `
        $FileResult.InfoCount, $FileResult.Path) -ForegroundColor $color
}

# ============================================================
# Main
# ============================================================

if (-not (Test-Path -LiteralPath $Path)) {
    Write-Error "Path does not exist: $Path"
    exit 2
}

$psExtensions = @('.ps1', '.psm1', '.psd1')

$files = Get-FilesToAudit -Root $Path -DoRecurse $Recurse `
                          -IncludeGlobs $Include -ExcludePatterns $ExcludePath
if (-not $files -or $files.Count -eq 0) {
    Write-Host "No files matched. Path=$Path Include=$($Include -join ',')" -ForegroundColor Yellow
    exit 0
}

if ($Format -ne 'json') {
    Write-Host ''
    Write-Host '=================================================' -ForegroundColor Magenta
    Write-Host '  Script Hygiene Audit' -ForegroundColor Magenta
    Write-Host '=================================================' -ForegroundColor Magenta
    Write-Host ''
    Write-Host ('Scanning {0} file(s) under: {1}' -f $files.Count, (Resolve-Path $Path)) -ForegroundColor Cyan
    Write-Host ''
}

$allResults = @()
foreach ($f in $files) {
    $isPs = $psExtensions -contains $f.Extension.ToLower()
    $r = Invoke-FileAudit -FilePath $f.FullName `
                          -IsPowerShell $isPs `
                          -AlsoCheckTrailingWS $CheckTrailingWhitespace.IsPresent
    $allResults += $r

    switch ($Format) {
        'text'    { Write-FileReportText    -FileResult $r }
        'summary' { Write-FileReportSummary -FileResult $r }
        'json'    { }   # batched at end
    }
}

# JSON output
if ($Format -eq 'json') {
    $payload = [pscustomobject]@{
        scanned_at  = (Get-Date).ToString('o')
        scan_root   = (Resolve-Path $Path).Path
        file_count  = $allResults.Count
        files       = $allResults
    }
    $payload | ConvertTo-Json -Depth 6
}

# Aggregate totals
$totalCritical = ($allResults | Measure-Object -Property CriticalCount -Sum).Sum
$totalWarning  = ($allResults | Measure-Object -Property WarningCount  -Sum).Sum
$totalInfo     = ($allResults | Measure-Object -Property InfoCount     -Sum).Sum
$totalErrors   = ($allResults | Where-Object { $_.ReadError }).Count

if ($Format -ne 'json') {
    Write-Host ''
    Write-Host '-------------------------------------------------' -ForegroundColor Magenta
    Write-Host ('Files scanned:  {0}' -f $allResults.Count)
    Write-Host ('Read errors:    {0}' -f $totalErrors) -ForegroundColor (& { if ($totalErrors -gt 0) { 'Red' } else { 'Gray' } })
    Write-Host ('Critical:       {0}' -f $totalCritical) -ForegroundColor (& { if ($totalCritical -gt 0) { 'Red' } else { 'Gray' } })
    Write-Host ('Warnings:       {0}' -f $totalWarning)  -ForegroundColor (& { if ($totalWarning -gt 0) { 'Yellow' } else { 'Gray' } })
    Write-Host ('Info:           {0}' -f $totalInfo)     -ForegroundColor DarkGray
    Write-Host '-------------------------------------------------' -ForegroundColor Magenta
    Write-Host ''
}

# Exit code
$exitCode = 0
switch ($FailOn) {
    'critical' {
        if ($totalCritical -gt 0 -or $totalErrors -gt 0) { $exitCode = 1 }
        if ($Strict -and $totalWarning -gt 0)            { $exitCode = 1 }
    }
    'warning' {
        if ($totalCritical -gt 0 -or $totalWarning -gt 0 -or $totalErrors -gt 0) { $exitCode = 1 }
    }
    'none' {
        $exitCode = 0
    }
}

exit $exitCode
