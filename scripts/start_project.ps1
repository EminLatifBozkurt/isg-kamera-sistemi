[CmdletBinding()]
param([switch]$SkipBrowser)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeDirectory = Join-Path $projectRoot "data\runtime"
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$frontendDirectory = Join-Path $projectRoot "frontend"
$frontendPackages = Join-Path $frontendDirectory "node_modules"
$postgresRoot = "C:\Program Files\PostgreSQL\18"
$postgresData = Join-Path $postgresRoot "data"
$pgCtlPath = Join-Path $postgresRoot "bin\pg_ctl.exe"
$psqlPath = Join-Path $postgresRoot "bin\psql.exe"
$panelUrl = "http://127.0.0.1:5173/"
$healthUrl = "http://127.0.0.1:8000/api/v1/health"

function Show-ErrorMessage {
    param([string]$Message)

    Write-Host "`nHATA: $Message" -ForegroundColor Red
    try {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show(
            $Message,
            "ISG Kamera Sistemi baslatilamadi",
            [System.Windows.MessageBoxButton]::OK,
            [System.Windows.MessageBoxImage]::Error
        ) | Out-Null
    }
    catch {
        # Grafik mesaj gösterilemezse terminaldeki hata metni yeterlidir.
    }
}

function Test-HttpEndpoint {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 400
    }
    catch {
        return $false
    }
}

function Assert-PortIsFree {
    param([int]$Port)

    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        throw "$Port portu baska bir uygulama tarafindan kullaniliyor. O uygulamayi kapatip tekrar dene."
    }
}

function Wait-ForEndpoint {
    param(
        [string]$Url,
        [string]$Name,
        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if (Test-HttpEndpoint -Url $Url) {
            return
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)

    throw "$Name $TimeoutSeconds saniye icinde hazir olmadi. data\runtime altindaki loglari kontrol et."
}

function Save-ProcessRecord {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$Name
    )

    $record = [PSCustomObject]@{
        pid = $Process.Id
        start_time_utc = $Process.StartTime.ToUniversalTime().ToString("o")
    }
    $recordPath = Join-Path $runtimeDirectory "$Name.json"
    $record | ConvertTo-Json | Set-Content -LiteralPath $recordPath -Encoding UTF8
}

$startedProcesses = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()
$databaseStarted = $false

try {
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw ".venv bulunamadi. Once README'deki Python kurulum adimlarini tamamla."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $frontendDirectory "package.json") -PathType Leaf)) {
        throw "frontend\package.json bulunamadi. Proje dosyalari eksik olabilir."
    }
    if (-not (Test-Path -LiteralPath $frontendPackages -PathType Container)) {
        throw "Arayuz paketleri kurulu degil. frontend klasorunde bir kez 'npm ci' calistir."
    }
    if (-not (Test-Path -LiteralPath $pgCtlPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $psqlPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $postgresData -PathType Container)) {
        throw "PostgreSQL 18 kurulumu bulunamadi. docs\POSTGRESQL_GELISTIRME_KURULUMU.md dosyasini kontrol et."
    }

    # Parola Git deposunda tutulmaz; kurulum sırasında Windows kullanıcı ortamına kaydedilir.
    $databasePassword = [Environment]::GetEnvironmentVariable("ISG_DATABASE_PASSWORD", "User")
    if ([string]::IsNullOrWhiteSpace($databasePassword)) {
        throw "ISG_DATABASE_PASSWORD Windows kullanici ortaminda bulunamadi."
    }
    $env:ISG_DATABASE_PASSWORD = $databasePassword
    $env:PGPASSWORD = $databasePassword

    & $pgCtlPath status -D $postgresData *> $null
    if ($LASTEXITCODE -ne 0) {
        & $pgCtlPath start -D $postgresData -l (Join-Path $postgresData "isg-postgresql.log") -w -t 30
        if ($LASTEXITCODE -ne 0) {
            throw "PostgreSQL baslatilamadi. data klasorundeki isg-postgresql.log dosyasini kontrol et."
        }
        $databaseStarted = $true
    }

    & $psqlPath -h 127.0.0.1 -p 5432 -U isg_app -d isg_kamera -tAc "SELECT 1" *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "PostgreSQL calisiyor ancak isg_app baglantisi dogrulanamadi."
    }
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue

    # Yeni şema sürümlerini API başlamadan önce uygularız. Migration başarısızsa
    # uygulama eski/uyumsuz tablo yapısıyla çalışıyor gibi gösterilmez.
    & $pythonPath -m alembic -c (Join-Path $projectRoot "backend\alembic.ini") upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Veritabani migration islemi tamamlanamadi."
    }

    $npmPath = (Get-Command npm.cmd -ErrorAction Stop).Source
    New-Item -ItemType Directory -Force -Path $runtimeDirectory | Out-Null

    if (-not (Test-HttpEndpoint -Url $healthUrl)) {
        Assert-PortIsFree -Port 8000
        $backendProcess = Start-Process `
            -FilePath $pythonPath `
            -ArgumentList @("-m", "uvicorn", "isg_api.main:app", "--host", "127.0.0.1", "--port", "8000") `
            -WorkingDirectory $projectRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $runtimeDirectory "backend.out.log") `
            -RedirectStandardError (Join-Path $runtimeDirectory "backend.err.log") `
            -PassThru
        $startedProcesses.Add($backendProcess)
        Save-ProcessRecord -Process $backendProcess -Name "backend"
    }

    if (-not (Test-HttpEndpoint -Url $panelUrl)) {
        Assert-PortIsFree -Port 5173
        $frontendProcess = Start-Process `
            -FilePath $npmPath `
            -ArgumentList @("run", "dev") `
            -WorkingDirectory $frontendDirectory `
            -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $runtimeDirectory "frontend.out.log") `
            -RedirectStandardError (Join-Path $runtimeDirectory "frontend.err.log") `
            -PassThru
        $startedProcesses.Add($frontendProcess)
        Save-ProcessRecord -Process $frontendProcess -Name "frontend"
    }

    Wait-ForEndpoint -Url $healthUrl -Name "FastAPI sunucusu"
    Wait-ForEndpoint -Url $panelUrl -Name "React paneli"

    # Normal çift tıklamada tarayıcı açılır; otomatik testte -SkipBrowser kullanılabilir.
    if (-not $SkipBrowser) {
        Start-Process $panelUrl
    }
    Write-Host "Proje hazir: $panelUrl" -ForegroundColor Green
    exit 0
}
catch {
    # Yalnizca bu calistirma sirasinda baslattigimiz surecleri geri kapatiriz.
    foreach ($process in $startedProcesses) {
        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
    if ($databaseStarted) {
        & $pgCtlPath stop -D $postgresData -m fast -w -t 30 *> $null
    }
    Show-ErrorMessage -Message $_.Exception.Message
    exit 1
}
