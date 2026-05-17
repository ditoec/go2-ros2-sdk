# Pin base image digests so the Docker layer cache is stable across builds.
# A floating/versioned tag can resolve to a new digest whenever Docker Hub
# publishes an update, busting every layer below FROM.
#
# Usage (run once from the project root, then commit the updated Dockerfiles):
#   docker pull ros:jazzy-ros-base
#   docker pull dustynv/ros:jazzy-ros-base-l4t-r36.4.0   # optional — Jetson only
#   .\docker\pin-base-image.ps1
#
# To intentionally upgrade later, re-pull then re-run this script.

$ErrorActionPreference = "Stop"

# ── Main Dockerfile ────────────────────────────────────────────────────────────
$dockerfile = Join-Path $PSScriptRoot "Dockerfile"
$digest = docker inspect --format='{{index .RepoDigests 0}}' ros:jazzy-ros-base 2>$null
if (-not $digest) {
    Write-Error "ros:jazzy-ros-base is not in the local Docker cache.`nRun first: docker pull ros:jazzy-ros-base"
    exit 1
}
$content = Get-Content $dockerfile -Raw
$updated = $content -replace 'FROM ros:[^\r\n]*', "FROM $digest"
Set-Content $dockerfile $updated -NoNewline
Write-Host "Pinned Dockerfile        to: $digest"

# ── Jetson Dockerfile ──────────────────────────────────────────────────────────
# The Jetson image is ARM64 and large — skip gracefully if not in local cache.
$jetsonDockerfile = Join-Path $PSScriptRoot "Dockerfile.jetson"
$jetsonImage = "dustynv/ros:jazzy-ros-base-l4t-r36.4.0"
$jetsonDigest = docker inspect --format='{{index .RepoDigests 0}}' $jetsonImage 2>$null
if (-not $jetsonDigest) {
    Write-Host "Skipping Dockerfile.jetson — $jetsonImage not in local cache."
    Write-Host "  To pin it: docker pull $jetsonImage  then re-run this script."
} else {
    $jetsonContent = Get-Content $jetsonDockerfile -Raw
    $jetsonUpdated = $jetsonContent -replace 'FROM dustynv/ros:[^\r\n]*', "FROM $jetsonDigest"
    Set-Content $jetsonDockerfile $jetsonUpdated -NoNewline
    Write-Host "Pinned Dockerfile.jetson to: $jetsonDigest"
}
