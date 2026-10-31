[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeDirectory = Join-Path $projectRoot "data\runtime"

function Stop-ProcessTree {
    param([int]$ProcessId)

    # npm, Vite'i alt surec olarak acar; once alt surecleri kapatiyoruz.
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        Stop-ProcessTree -ProcessId $child.ProcessId
    }
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Stop-RecordedProcess {
    param([string]$Name)

    $recordPath = Join-Path $runtimeDirectory "$Name.json"
    if (-not (Test-Path -LiteralPath $recordPath -PathType Leaf)) {
        return $false
    }

    $record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
    $process = Get-Process -Id ([int]$record.pid) -ErrorAction SilentlyContinue
    if ($process) {
        $actualStart = $process.StartTime.ToUniversalTime().ToString("o")
        if ($actualStart -eq [string]$record.start_time_utc) {
            Stop-ProcessTree -ProcessId $process.Id
        }
        else {
            Write-Warning "$Name PID kaydi eski; baska bir surec guvenlik icin kapatilmadi."
        }
    }

    Remove-Item -LiteralPath $recordPath -Force
    return $true
}

try {
    $backendStopped = Stop-RecordedProcess -Name "backend"
    $frontendStopped = Stop-RecordedProcess -Name "frontend"

    if ($backendStopped -or $frontendStopped) {
        Write-Host "ISG Kamera Sistemi arka plan surecleri durduruldu." -ForegroundColor Green
    }
    else {
        Write-Host "Bu baslaticinin kaydettigi calisan bir proje sureci bulunamadi." -ForegroundColor Yellow
    }
    exit 0
}
catch {
    Write-Host "`nHATA: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
