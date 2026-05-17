#!/usr/bin/env bash
# Pin base image digests so the Docker layer cache is stable across builds.
# A floating/versioned tag can resolve to a new digest whenever Docker Hub
# publishes an update, busting every layer below FROM.
#
# Usage (run once, then commit the updated Dockerfiles):
#   docker pull ros:jazzy-ros-base
#   docker pull dustynv/ros:jazzy-ros-base-l4t-r36.4.0   # optional — Jetson only
#   bash docker/pin-base-image.sh
#
# To intentionally upgrade later, re-pull then re-run this script.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Main Dockerfile ────────────────────────────────────────────────────────────
DOCKERFILE="$DIR/Dockerfile"
DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' ros:jazzy-ros-base 2>/dev/null) || {
  echo "ERROR: ros:jazzy-ros-base is not in the local Docker cache." >&2
  echo "Run first: docker pull ros:jazzy-ros-base" >&2
  exit 1
}
if [[ -z "$DIGEST" ]]; then
  echo "ERROR: could not read digest for ros:jazzy-ros-base." >&2
  exit 1
fi
sed -i "s|^FROM ros:[^ ]*|FROM ${DIGEST}|" "$DOCKERFILE"
echo "Pinned Dockerfile        to: ${DIGEST}"

# ── Jetson Dockerfile ──────────────────────────────────────────────────────────
# The Jetson image is ARM64 and large — skip gracefully if not in local cache.
JETSON_DOCKERFILE="$DIR/Dockerfile.jetson"
JETSON_IMAGE="dustynv/ros:jazzy-ros-base-l4t-r36.4.0"
JETSON_DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "$JETSON_IMAGE" 2>/dev/null || true)
if [[ -z "$JETSON_DIGEST" ]]; then
  echo "Skipping Dockerfile.jetson — $JETSON_IMAGE not in local cache."
  echo "  To pin it: docker pull $JETSON_IMAGE  then re-run this script."
else
  sed -i "s|^FROM dustynv/ros:[^ ]*|FROM ${JETSON_DIGEST}|" "$JETSON_DOCKERFILE"
  echo "Pinned Dockerfile.jetson to: ${JETSON_DIGEST}"
fi
