<#
.SYNOPSIS
    Builds tectonica.dll from the vendor/tectonica submodule and copies it into the repo root,
    where dwgmagic's generated .scr scripts expect to NETLOAD it.
.PARAMETER Configuration
    MSBuild configuration to build (default: Release).
#>
param(
    [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$SubmodulePath = Join-Path $RepoRoot "vendor\tectonica"
$SolutionPath = Join-Path $SubmodulePath "tectonica.sln"

if (-not (Test-Path $SolutionPath)) {
    Write-Host "vendor/tectonica is missing or empty. Initializing submodule..."
    git -C $RepoRoot submodule update --init --recursive
}

if (-not (Test-Path $SolutionPath)) {
    throw "Could not find $SolutionPath after initializing the submodule."
}

function Find-MSBuild {
    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswhere) {
        $msbuildPath = & $vswhere -latest -requires Microsoft.Component.MSBuild -find MSBuild\**\Bin\MSBuild.exe | Select-Object -First 1
        if ($msbuildPath) { return $msbuildPath }
    }

    $candidates = @(
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe",
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe",
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe",
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\MSBuild.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) { return $candidate }
    }

    throw "MSBuild.exe not found. Install Visual Studio or the Visual Studio Build Tools."
}

$MSBuild = Find-MSBuild
Write-Host "Using MSBuild: $MSBuild"

& $MSBuild $SolutionPath "/t:Restore" "/nologo" "/verbosity:minimal"
if ($LASTEXITCODE -ne 0) {
    throw "NuGet restore failed with exit code $LASTEXITCODE"
}

& $MSBuild $SolutionPath "/p:Configuration=$Configuration" "/p:Platform=Any CPU" "/nologo" "/verbosity:minimal"
if ($LASTEXITCODE -ne 0) {
    throw "MSBuild failed with exit code $LASTEXITCODE"
}

$BuiltDll = Join-Path $SubmodulePath "tectonica\bin\$Configuration\net8.0-windows\tectonica.dll"
if (-not (Test-Path $BuiltDll)) {
    throw "Build succeeded but $BuiltDll was not found."
}

Copy-Item -Path $BuiltDll -Destination (Join-Path $RepoRoot "tectonica.dll") -Force

$BuiltPdb = Join-Path $SubmodulePath "tectonica\bin\$Configuration\net8.0-windows\tectonica.pdb"
if (Test-Path $BuiltPdb) {
    Copy-Item -Path $BuiltPdb -Destination (Join-Path $RepoRoot "tectonica.pdb") -Force
}

Write-Host "tectonica.dll built and copied to $RepoRoot\tectonica.dll"
