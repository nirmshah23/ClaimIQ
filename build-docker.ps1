[CmdletBinding()]
param(
    [string]$ImageName = "claimcraft",
    [string]$Tag = "latest",
    [string]$Dockerfile = "Dockerfile",
    [string]$Context = ".",
    [string]$TarPath,
    [switch]$NoCache,
    [switch]$Pull,
    [switch]$Push
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-ScriptPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }

    return [System.IO.Path]::GetFullPath((Join-Path -Path $PSScriptRoot -ChildPath $Path))
}

function Assert-CommandExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CommandName
    )

    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "Required command '$CommandName' was not found in PATH."
    }
}

Assert-CommandExists -CommandName "docker"

$dockerfilePath = Resolve-ScriptPath -Path $Dockerfile
$contextPath = Resolve-ScriptPath -Path $Context

if (-not (Test-Path -LiteralPath $dockerfilePath -PathType Leaf)) {
    throw "Dockerfile not found: $dockerfilePath"
}

if (-not (Test-Path -LiteralPath $contextPath -PathType Container)) {
    throw "Build context directory not found: $contextPath"
}

try {
    docker version | Out-Null
} catch {
    throw "Docker is installed but not responding. Start Docker Desktop or the Docker daemon and try again."
}

$imageRef = "{0}:{1}" -f $ImageName.ToLowerInvariant(), $Tag
$safeImageName = $ImageName.ToLowerInvariant().Replace("/", "-").Replace("\", "-")

if ([string]::IsNullOrWhiteSpace($TarPath)) {
    $TarPath = "{0}-{1}.tar" -f $safeImageName, $Tag
}

$tarFilePath = Resolve-ScriptPath -Path $TarPath
$dockerArgs = @(
    "build",
    "--file", $dockerfilePath,
    "--tag", $imageRef
)

if ($NoCache) {
    $dockerArgs += "--no-cache"
}

if ($Pull) {
    $dockerArgs += "--pull"
}

$dockerArgs += $contextPath

Write-Host "Building image: $imageRef"
Write-Host "Dockerfile: $dockerfilePath"
Write-Host "Context: $contextPath"
Write-Host ""

& docker @dockerArgs

if ($LASTEXITCODE -ne 0) {
    throw "Docker build failed with exit code $LASTEXITCODE."
}

Write-Host ""
Write-Host "Build completed successfully: $imageRef"
Write-Host "Saving image tar: $tarFilePath"

& docker save --output $tarFilePath $imageRef

if ($LASTEXITCODE -ne 0) {
    throw "Docker save failed with exit code $LASTEXITCODE."
}

Write-Host "Image tar saved successfully: $tarFilePath"

if ($Push) {
    Write-Host "Pushing image: $imageRef"
    & docker push $imageRef

    if ($LASTEXITCODE -ne 0) {
        throw "Docker push failed with exit code $LASTEXITCODE."
    }

    Write-Host "Push completed successfully: $imageRef"
}
