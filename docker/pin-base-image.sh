#!/usr/bin/env bash
# Pin the ROS base image to its current local digest so the Docker layer cache
# is stable across builds.  A floating tag like ros:jazzy-ros-base can resolve
# to a new digest whenever Docker Hub publishes an update, busting every layer
# below FROM even when your own code hasn't changed.
#
# Usage (run once, then commit the updated Dockerfile):
#   docker pull ros:jazzy-ros-base   # fetch the version you want to pin
#   bash docker/pin-base-image.sh
#
# To intentionally upgrade later:
#   docker pull ros:jazzy-ros-base && bash docker/pin-base-image.sh
set -euo pipefail

DOCKERFILE="$(cd "$(dirname "$0")" && pwd)/Dockerfile"

DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' ros:jazzy-ros-base 2>/dev/null) || {
  echo "ERROR: ros:jazzy-ros-base is not in the local Docker cache." >&2
  echo "Run first: docker pull ros:jazzy-ros-base" >&2
  exit 1
}

if [[ -z "$DIGEST" ]]; then
  echo "ERROR: could not read digest for ros:jazzy-ros-base." >&2
  exit 1
fi

# Replace the FROM line (with or without a previously pinned digest)
sed -i "s|^FROM ros:jazzy-ros-base.*|FROM ${DIGEST}|" "$DOCKERFILE"
echo "Pinned Dockerfile to: ${DIGEST}"
