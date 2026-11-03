# Phase 0 feasibility check for the TPC-H-derived experiments.
# Run from backend\ in PowerShell (LibreHardwareMonitor should be running as Administrator):
#   .\scripts\Check-TpchFeasibility.ps1
# Writes a report to .\feasibility-report.txt and prints it. Nothing is changed on the machine.

$ErrorActionPreference = "Continue"
$report = New-Object System.Collections.Generic.List[string]
function Out([string]$s) { $report.Add($s); Write-Host $s }
function Section([string]$s) { Out ""; Out ("=" * 70); Out $s; Out ("=" * 70) }

Section "1. Machine"
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$os = Get-CimInstance Win32_OperatingSystem
Out ("CPU:            {0} ({1} cores / {2} logical, {3} MHz max)" -f $cpu.Name.Trim(), $cpu.NumberOfCores, $cpu.NumberOfLogicalProcessors, $cpu.MaxClockSpeed)
Out ("RAM:            {0:N1} GB total, {1:N1} GB free" -f ($os.TotalVisibleMemorySize/1MB), ($os.FreePhysicalMemory/1MB))
Out ("OS:             {0} build {1}" -f $os.Caption, $os.BuildNumber)
$drive = Get-PSDrive -Name ($PWD.Drive.Name)
Out ("Disk {0}:        {1:N1} GB free of {2:N1} GB   (TPC-H SF1 needs ~4 GB incl. indexes; SF0.3 ~1.5 GB)" -f $drive.Name, ($drive.Free/1GB), (($drive.Used+$drive.Free)/1GB))
$pgData = $null
try { $pgData = (& psql -U greencode -d greencode -tAc "SHOW data_directory;" 2>$null) } catch {}
if ($pgData) { Out ("PG data dir:    {0}" -f $pgData.Trim()) }

Section "2. Power"
$bat = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue
if ($bat) { Out ("Battery:        {0}% ; status code {1} (2 = on AC)" -f $bat.EstimatedChargeRemaining, $bat.BatteryStatus) } else { Out "Battery:        none detected (desktop?)" }
Out "Power plans (powercfg /list):"
& powercfg /list 2>&1 | ForEach-Object { Out ("   " + $_) }
Out "Active scheme:"
& powercfg /getactivescheme 2>&1 | ForEach-Object { Out ("   " + $_) }
$overlay = $null
try { $overlay = (& powercfg /overlaygetactivescheme 2>&1) } catch {}
if ($overlay) { Out "Power mode overlay (slider):"; $overlay | ForEach-Object { Out ("   " + $_) } }

Section "3. PostgreSQL configuration"
$pgq = @"
SELECT name, setting, unit FROM pg_settings WHERE name IN
('shared_buffers','work_mem','maintenance_work_mem','effective_cache_size','max_parallel_workers_per_gather',
 'max_worker_processes','jit','random_page_cost','server_version','data_checksums','wal_level','synchronous_commit')
ORDER BY name;
"@
$py = @"
import sys; sys.path.insert(0, '.')
import psycopg
from app.config import get_settings
with psycopg.connect(get_settings().benchmark_database_url) as c:
    for name, setting, unit in c.execute("""SELECT name, setting, unit FROM pg_settings WHERE name IN
      ('shared_buffers','work_mem','maintenance_work_mem','effective_cache_size','max_parallel_workers_per_gather',
       'max_worker_processes','jit','random_page_cost','server_version','wal_level','synchronous_commit') ORDER BY name"""):
        print(f"   {name:32s} {setting} {unit or ''}")
    print("   greencode database size:", c.execute("SELECT pg_size_pretty(pg_database_size(current_database()))").fetchone()[0])
"@
try { & python -c $py 2>&1 | ForEach-Object { Out $_ } } catch { Out "   could not query PostgreSQL: $_" }

Section "4. LibreHardwareMonitor sensors"
try {
  $json = Invoke-RestMethod -Uri "http://localhost:8085/data.json" -TimeoutSec 3
  $found = New-Object System.Collections.Generic.List[string]
  function Walk($node, $path) {
    $p = if ($node.Text) { "$path/$($node.Text)" } else { $path }
    if ($node.SensorId -and ($node.SensorId -match "/power/" -or $node.SensorId -match "/temperature/")) {
      $found.Add(("   {0,-60} {1,10}   {2}" -f $node.SensorId, $node.Value, $p))
    }
    foreach ($c in $node.Children) { Walk $c $p }
  }
  Walk $json ""
  $found | ForEach-Object { Out $_ }
  $dram = $found | Where-Object { $_ -match "(?i)dram|memory" -and $_ -match "/power/" }
  if ($dram) { Out "   -> DRAM power sensor PRESENT: the 'before/after DRAM' stage is feasible." }
  else { Out "   -> NO DRAM power sensor: RAPL on this CPU exposes package only. The DRAM stage must be reframed (package energy on memory-heavy queries)." }
  $pkg = $found | Where-Object { $_ -match "(?i)package" -and $_ -match "/power/" }
  if ($pkg) { Out "   -> CPU package power sensor present (what GreenCode reads)." } else { Out "   -> WARNING: no CPU package power sensor found." }
} catch { Out "   LHM web server not reachable at http://localhost:8085/data.json (start LHM as Administrator, Options > Remote Web Server > Run)" }

Section "5. Background activity snapshot (Task Manager view)"
$procs = Get-Process
Out ("Processes:      {0}" -f $procs.Count)
Out "Top 12 by CPU time:"
$procs | Sort-Object CPU -Descending | Select-Object -First 12 | ForEach-Object { Out ("   {0,-30} CPU {1,8:N1}s  WS {2,7:N0} MB" -f $_.ProcessName, $_.CPU, ($_.WorkingSet64/1MB)) }
$watch = "ollama","MsMpEng","SearchIndexer","OneDrive","Teams","chrome","msedge","Code","Dropbox","Spotify","Discord","steam","wuauclt","TiWorker","MoUsoCoreWorker"
$hits = $procs | Where-Object { $watch -contains $_.ProcessName } | Select-Object -ExpandProperty ProcessName -Unique
Out ("Noisy processes present: " + ($(if ($hits) { $hits -join ", " } else { "none of the usual suspects" })))
$svc = Get-Service -Name "wuauserv","WSearch","SysMain","DiagTrack" -ErrorAction SilentlyContinue
$svc | ForEach-Object { Out ("   service {0,-12} {1}" -f $_.Name, $_.Status) }

Section "6. Idle power trace (60 s, LHM package power every 1 s)"
try {
  $samples = @(); $temps = @()
  for ($i = 0; $i -lt 60; $i++) {
    $j = Invoke-RestMethod -Uri "http://localhost:8085/data.json" -TimeoutSec 2
    $v = $null; $t = $null
    function Find($node) {
      if ($node.SensorId -and $node.SensorId -match "/power/" -and $node.Text -match "(?i)package") { $script:v = $node.Value }
      if ($node.SensorId -and $node.SensorId -match "/temperature/" -and $node.Text -match "(?i)package|core average") { if (-not $script:t) { $script:t = $node.Value } }
      foreach ($c in $node.Children) { Find $c }
    }
    Find $j
    if ($v) { $samples += [double](($v -replace "[^\d.,]", "") -replace ",", ".") }
    if ($t) { $temps += [double](($t -replace "[^\d.,]", "") -replace ",", ".") }
    Start-Sleep -Seconds 1
  }
  if ($samples.Count) {
    $s = $samples | Measure-Object -Minimum -Maximum -Average
    Out ("Package power: min {0:N2} W  mean {1:N2} W  max {2:N2} W  ({3} readings)" -f $s.Minimum, $s.Average, $s.Maximum, $samples.Count)
    $distinct = ($samples | Select-Object -Unique).Count
    Out ("Distinct values: {0}  (LHM refresh ~1 s; expect ~50-60)" -f $distinct)
    if ($s.Maximum -gt 2 * $s.Minimum) { Out "   -> Idle is NOISY (max > 2x min): background activity present; the protocol must quieten the machine." } else { Out "   -> Idle is reasonably stable." }
  }
  if ($temps.Count) { $t = $temps | Measure-Object -Minimum -Maximum -Average; Out ("CPU temperature: {0:N0}-{1:N0} C at idle" -f $t.Minimum, $t.Maximum) }
} catch { Out "   trace skipped (LHM not reachable)" }

Section "7. Python / DuckDB"
try { $py = & python --version 2>&1; Out ("Python:         " + $py) } catch {}
try { $dd = & python -c "import duckdb; print(duckdb.__version__)" 2>&1; Out ("duckdb:         " + $dd + "   (used to generate TPC-H data; 'pip install --user duckdb' if missing)") } catch {}
try { $ps = & python -c "import psutil, psycopg; print('psutil', psutil.__version__, 'psycopg', psycopg.__version__)" 2>&1; Out ("libs:           " + $ps) } catch {}

Section "8. Verdict"
Out "Send feasibility-report.txt back for interpretation. Key decisions: scale factor (SF1 vs SF0.3), DRAM stage in/out, which power plans exist, how noisy idle is."
$report | Set-Content -Path ".\feasibility-report.txt" -Encoding UTF8
Out ""
Out "Written to .\feasibility-report.txt"
