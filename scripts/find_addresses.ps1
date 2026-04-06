# PowerShell: Find Bitcoin address files on your Windows machine
# Run this on DESKTOP-ME2NGP6

$searchPaths = @(
    "C:\Users\nick\source\repos\BitCrack",
    "C:\Users\nick\Desktop",
    "C:\Users\nick\Documents",
    "C:\Users\nick"
)

Write-Host "=== Searching for address/target files ===" -ForegroundColor Cyan

foreach ($path in $searchPaths) {
    if (Test-Path $path) {
        Write-Host "`nSearching: $path" -ForegroundColor Yellow
        Get-ChildItem -Path $path -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Extension -in '.txt','.csv','.dat','.list','.json' } |
            ForEach-Object {
                $lineCount = (Get-Content $_.FullName -ErrorAction SilentlyContinue | Measure-Object -Line).Lines
                $firstLine = Get-Content $_.FullName -First 1 -ErrorAction SilentlyContinue
                Write-Host "  $($_.FullName) ($lineCount lines) -> $firstLine"
            }
    }
}

# Also check for files with "million" or "address" or "target" in the name
Write-Host "`n=== Files matching *million*, *address*, *target*, *dormant*, *wallet* ===" -ForegroundColor Cyan
foreach ($path in $searchPaths) {
    if (Test-Path $path) {
        Get-ChildItem -Path $path -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match 'million|address|target|dormant|wallet|btc' } |
            ForEach-Object {
                Write-Host "  FOUND: $($_.FullName) ($($_.Length) bytes)"
            }
    }
}
