# Pin the ROS base image to its current local digest so the Docker layer cache
# is stable across builds.
#
# Usage (run once from the project root, then commit the updated Dockerfile):
#   docker pull ros:jazzy-ros-base
#   .\docker\pin-base-image.ps1
#
# To intentionally upgrade later:
#   docker pull ros:jazzy-ros-base; .\docker\pin-base-image.ps1

$ErrorActionPreference = "Stop"

$dockerfile = Join-Path $PSScriptRoot "Dockerfile"

$digest = docker inspect --format='{{index .RepoDigests 0}}' ros:jazzy-ros-base 2>$null
if (-not $digest) {
    Write-Error "ros:jazzy-ros-base is not in the local Docker cache.`nRun first: docker pull ros:jazzy-ros-base"
    exit 1
}

$content = Get-Content $dockerfile -Raw
$updated = $content -replace 'FROM ros:jazzy-ros-base[^\r\n]*', "FROM $digest"
Set-Content $dockerfile $updated -NoNewline
Write-Host "Pinned Dockerfile to: $digest"
