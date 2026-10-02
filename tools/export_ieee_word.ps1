<#
Export the generated IEEE DOCX with installed Microsoft Word on Windows.
Word balances continuous column sections more reliably for this manuscript
than the tested LibreOffice renderer. The source opens read-only and is not
saved. Inspect the exported PDF before copying it into paper/.
#>
param([string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$repositoryPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$inputPath = Join-Path $repositoryPath 'paper\Revon_Research_Paper_IEEE.docx'
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $repositoryPath '.codex_tmp\seven_revisions\render-ieee-word'
}
$exportDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $exportDirectory -Force | Out-Null
$outputPath = Join-Path $exportDirectory 'Revon_Research_Paper_IEEE.pdf'
$wordApplication = $null
$wordDocument = $null
try {
    $wordApplication = New-Object -ComObject Word.Application
    $wordApplication.Visible = $false
    $wordApplication.DisplayAlerts = 0
    $wordDocument = $wordApplication.Documents.Open($inputPath, $false, $true)
    $wordDocument.Repaginate()
    $wordDocument.ExportAsFixedFormat($outputPath, 17)
    Write-Output $outputPath
} finally {
    if ($null -ne $wordDocument) { $wordDocument.Close(0) }
    if ($null -ne $wordApplication) { $wordApplication.Quit(0) }
}
