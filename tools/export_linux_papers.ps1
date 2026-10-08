$ErrorActionPreference = 'Stop'
$wordApplication = $null
try {
    $wordApplication = New-Object -ComObject Word.Application
    $wordApplication.Visible = $false
    $wordApplication.DisplayAlerts = 0
    foreach ($formatName in @('Discover_Computing', 'IEEE')) {
        $inputPath = (Resolve-Path -LiteralPath "paper\Revon_Research_Paper_$formatName.docx").Path
        $outputPath = [System.IO.Path]::ChangeExtension($inputPath, '.pdf')
        $wordDocument = $null
        try {
            $wordDocument = $wordApplication.Documents.Open($inputPath, $false, $true)
            $wordDocument.Repaginate()
            $wordDocument.ExportAsFixedFormat($outputPath, 17)
            Write-Output $outputPath
        } finally {
            if ($null -ne $wordDocument) { $wordDocument.Close(0) }
        }
    }
} finally {
    if ($null -ne $wordApplication) { $wordApplication.Quit() }
}
