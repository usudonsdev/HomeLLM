# Local probe for Valorant .dem files (research only — not a product pipeline).
# Does not claim the format is parseable; prints headers / heuristics only.
param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Path)) {
    throw "File not found: $Path"
}

$item = Get-Item -LiteralPath $Path
Write-Host "=== Valorant .dem probe (research) ==="
Write-Host ("path:     " + $item.FullName)
Write-Host ("size:     {0:N0} bytes ({1:N2} MiB)" -f $item.Length, ($item.Length / 1MB))
Write-Host ("mtime:    " + $item.LastWriteTime.ToString("o"))

$fs = [System.IO.File]::OpenRead($item.FullName)
try {
    $headLen = [Math]::Min(256, [int]$item.Length)
    $buf = New-Object byte[] $headLen
    [void]$fs.Read($buf, 0, $headLen)
}
finally {
    $fs.Close()
}

$hex = ($buf | ForEach-Object { $_.ToString("X2") }) -join " "
Write-Host ""
Write-Host ("first {0} bytes (hex):" -f $headLen)
Write-Host $hex

# Printable ASCII runs in the header
$chars = New-Object System.Collections.Generic.List[string]
$run = ""
foreach ($b in $buf) {
    if ($b -ge 32 -and $b -le 126) {
        $run += [char]$b
    } else {
        if ($run.Length -ge 4) { [void]$chars.Add($run) }
        $run = ""
    }
}
if ($run.Length -ge 4) { [void]$chars.Add($run) }

Write-Host ""
Write-Host "ASCII runs (>=4) in header:"
if ($chars.Count -eq 0) {
    Write-Host "  (none)"
} else {
    $chars | Select-Object -First 20 | ForEach-Object { Write-Host ("  " + $_) }
}

# Crude Source2-ish magic check (PBDEMS2 / HL2DEMO variants used by Valve demos)
$asciiHead = [System.Text.Encoding]::ASCII.GetString($buf)
$looksLikeValve = ($asciiHead -match "PBDEMS2|HL2DEMO|DEMOS")
Write-Host ""
Write-Host ("looks_like_valve_source_demo_magic: " + $looksLikeValve)
if (-not $looksLikeValve) {
    Write-Host "Hint: CS2/Dota Source2 parsers will likely fail. Treat as proprietary until proven otherwise."
}

Write-Host ""
Write-Host "Next manual checks:"
Write-Host "  1) Try opening with a CS2 demo tool — expect failure if proprietary."
Write-Host "  2) Compare two .dem from different maps for repeating structure."
Write-Host "  3) Record findings in docs/research/valorant_dem_spike.md"
Write-Host ""
Write-Host "Do not commit .dem files."
