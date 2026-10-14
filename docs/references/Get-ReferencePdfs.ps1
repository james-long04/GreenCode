# Downloads the open-access PDFs for the GreenCode references into .\pdfs\ so that
# importing greencode-references.bib into Zotero attaches them. Run from this folder:
#   powershell -ExecutionPolicy Bypass -File .\Get-ReferencePdfs.ps1

$ErrorActionPreference = "Continue"
$dir = Join-Path $PSScriptRoot "pdfs"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$pdfs = @{
  "connollybree2025impact" = "https://researchrepository.ucd.ie/server/api/core/bitstreams/0102f552-ecc3-4d24-a9f8-6d6a8106e369/content"
  "ferreira2018javascript" = "https://arrow.tudublin.ie/cgi/viewcontent.cgi?article=1142&context=scschcomdis"
  "yadav2026idea" = "https://arrow.tudublin.ie/cgi/viewcontent.cgi?article=1000&context=cenresro"
  "lannelongue2021green" = "https://onlinelibrary.wiley.com/doi/pdf/10.1002/advs.202100707"
  "chen2021codex" = "https://arxiv.org/pdf/2107.03374"
  "huang2024effibench" = "https://arxiv.org/pdf/2402.02037"
  "du2024mercury" = "https://arxiv.org/pdf/2402.07844"
  "shypula2024learning" = "https://arxiv.org/pdf/2302.07867"
  "cursaru2024controlled" = "https://arxiv.org/pdf/2405.03616"
  "vartziotis2024learn" = "https://arxiv.org/pdf/2403.03344"
  "solovyeva2025aipowered" = "https://arxiv.org/pdf/2502.02412"
  "islam2025evaluating" = "https://arxiv.org/pdf/2505.20324"
  "apsan2025generating" = "https://arxiv.org/pdf/2509.10099"
  "peng2024llms" = "https://arxiv.org/pdf/2410.09241"
  "romerorosas2024should" = "https://arxiv.org/pdf/2406.12146"
  "li2024llmr2" = "https://arxiv.org/pdf/2404.12872"
  "georges2007statistically" = "https://users.elis.ugent.be/~leeckhou/papers/oopsla07-georges.pdf"
}
$ok = 0; $failed = @()
foreach ($key in $pdfs.Keys) {
  $out = Join-Path $dir "$key.pdf"
  try {
    Invoke-WebRequest -Uri $pdfs[$key] -OutFile $out -UserAgent "Mozilla/5.0" -MaximumRedirection 10 -TimeoutSec 120
    $head = [System.IO.File]::ReadAllBytes($out)[0..3]
    if ([System.Text.Encoding]::ASCII.GetString($head) -ne "%PDF") { throw "not a PDF (probably an HTML landing page)" }
    Write-Host ("ok      {0}" -f $key); $ok++
  } catch {
    Write-Host ("FAILED  {0}: {1}" -f $key, $_.Exception.Message) -ForegroundColor Yellow
    Remove-Item -Force -ErrorAction SilentlyContinue $out
    $failed += $key
  }
}
Write-Host ""
Write-Host ("Downloaded {0} of {1} open-access PDFs." -f $ok, $pdfs.Count)
if ($failed) { Write-Host ("Could not fetch: {0}" -f ($failed -join ", ")) }
Write-Host "Not open access (use the DOI through the TU Dublin library): pinto2017energy, lee2024survey, pereira2021ranking, khan2018rapl, abtahi2025augmenting, mytkowicz2009producing, gsf2024sci (web page)."
