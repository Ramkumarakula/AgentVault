# Opens the generated report in Microsoft Word, updates the index (TOC) and page fields,
# saves the .docx and exports a PDF next to it. Windows + Word only.
#   powershell -ExecutionPolicy Bypass -File report/finalize_word.ps1
$ErrorActionPreference = "Stop"
$docx = (Resolve-Path (Join-Path $PSScriptRoot "AgentVault_Report.docx")).Path
$pdf  = [System.IO.Path]::ChangeExtension($docx, ".pdf")

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($docx)
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    $doc.Fields.Update() | Out-Null
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }   # second pass after pagination settles
    $doc.Save()
    $doc.ExportAsFixedFormat($pdf, 17)   # 17 = wdExportFormatPDF
    $pages = $doc.ComputeStatistics(2)   # 2 = wdStatisticPages
    $doc.Close()
    Write-Output "updated TOC, saved $docx, exported $pdf ($pages pages)"
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
