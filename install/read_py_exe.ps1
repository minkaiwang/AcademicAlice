param(
    [Parameter(Mandatory = $true)]
    [string] $ProjectRoot
)
$ini = Join-Path $ProjectRoot 'py.ini'
if (-not (Test-Path -LiteralPath $ini)) {
    exit 0
}
$line = Get-Content -LiteralPath $ini -Encoding UTF8 |
    Where-Object { $_ -match '^\s*python_executable\s*=' } |
    Select-Object -First 1
if ($null -eq $line) {
    exit 0
}
Write-Output (($line -replace '^\s*python_executable\s*=\s*', '').Trim())
