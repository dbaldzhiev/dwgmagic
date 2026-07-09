<#
.SYNOPSIS
    Updates a DWGMAGIC installation in place.
.DESCRIPTION
    Git checkouts are updated with `git pull --ff-only`; installed copies are
    updated by downloading the latest GitHub release archive and copying it
    over the application directory (preserving venv/, logs/, tectonica.dll).
    Invoked via update.bat, which copies this script to TEMP first so the
    running updater is never overwritten by itself.
.PARAMETER AppDir
    The DWGMAGIC application directory to update.
.PARAMETER Relaunch
    Reopen the GUI once the update completes.
#>
param(
    [Parameter(Mandatory = $true)][string]$AppDir,
    [switch]$Relaunch
)

$ErrorActionPreference = "Stop"
$LogPath = Join-Path $env:TEMP "dwgmagic_update.log"
Start-Transcript -Path $LogPath -Force | Out-Null

try {
    $AppDir = (Resolve-Path -LiteralPath $AppDir).ProviderPath
    Write-Host "Updating DWGMAGIC at $AppDir"
    Start-Sleep -Seconds 2  # allow the GUI process to exit before touching files

    if (Test-Path (Join-Path $AppDir ".git")) {
        Write-Host "Git checkout detected; pulling latest changes..."
        git -C $AppDir pull --ff-only
        if ($LASTEXITCODE -ne 0) { throw "git pull failed with exit code $LASTEXITCODE" }
    }
    else {
        Write-Host "Fetching latest release information from GitHub..."
        $repo = "dbaldzhiev/dwgmagic"
        $headers = @{ "User-Agent" = "dwgmagic-updater"; "Accept" = "application/vnd.github+json" }
        $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/releases/latest" -Headers $headers
        $tag = $release.tag_name
        Write-Host "Latest release: $tag"

        $zipPath = Join-Path $env:TEMP "dwgmagic_update.zip"
        $extractDir = Join-Path $env:TEMP "dwgmagic_update_extract"
        Write-Host "Downloading $($release.zipball_url)..."
        Invoke-WebRequest -Uri $release.zipball_url -Headers $headers -OutFile $zipPath
        if (Test-Path $extractDir) { Remove-Item -Recurse -Force $extractDir }
        Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
        $inner = Get-ChildItem -Directory $extractDir | Select-Object -First 1
        if (-not $inner) { throw "Release archive was empty" }

        Write-Host "Applying update..."
        robocopy $inner.FullName $AppDir /E /R:2 /W:5 /XD ".git" "venv" ".venv" "logs" "__pycache__" /NFL /NDL /NJH /NJS | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "robocopy failed with exit code $LASTEXITCODE" }

        Remove-Item -Force $zipPath -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force $extractDir -ErrorAction SilentlyContinue
    }

    $venvPython = Join-Path $AppDir "venv\Scripts\python.exe"
    $requirements = Join-Path $AppDir "requirements.txt"
    if ((Test-Path $venvPython) -and (Test-Path $requirements)) {
        Write-Host "Updating Python dependencies..."
        & $venvPython -m pip install -r $requirements --quiet
        if ($LASTEXITCODE -ne 0) { Write-Warning "pip install reported errors; see $LogPath" }
    }

    Write-Host "Update complete."
    if ($Relaunch) {
        $launcher = Join-Path $AppDir "run_gui.bat"
        if (Test-Path $launcher) {
            Write-Host "Relaunching DWGMAGIC..."
            Start-Process -FilePath $launcher -WorkingDirectory $AppDir
        }
    }
    Start-Sleep -Seconds 2
}
catch {
    Write-Host ""
    Write-Host "Update failed: $_" -ForegroundColor Red
    Write-Host "Details were logged to $LogPath"
    Write-Host "Press Enter to close..."
    Read-Host | Out-Null
    exit 1
}
finally {
    Stop-Transcript | Out-Null
}
