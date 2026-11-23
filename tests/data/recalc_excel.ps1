# Step 2 of 2 for the golden test file (step 1: make_golden.py).
# Opens golden_example.xlsx in Excel, recalculates every formula and saves,
# so cached values in Hasil and Periksa are Excel's own results.
# Needs Microsoft Excel on Windows. Run:
#     powershell -File tests\data\recalc_excel.ps1

$ErrorActionPreference = 'Stop'
$path = Join-Path $PSScriptRoot 'golden_example.xlsx'
if (-not (Test-Path -LiteralPath $path)) { throw "Not found: $path (run make_golden.py first)" }

$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false
$xl.DisplayAlerts = $false
try {
    $wb = $xl.Workbooks.Open($path)
    $xl.CalculateFull()
    $wb.Save()
    $wb.Close($false)
    Write-Host "Recalculated and saved: $path"
}
finally {
    $xl.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null
}
