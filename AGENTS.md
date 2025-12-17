# AGENTS.md

This file provides guidance to [agents](https://agents.md/) when working with code in this repository.

## Repository Purpose

This repository contains custom container images built and maintained by Wiremind, published to GitHub Container Registry (ghcr.io/wiremind/).

## Architecture

Each image lives in its own directory with two files:

- `Containerfile` - Build instructions using `ARG UPSTREAM_TAG` for the base image version
- `versions.yaml` - List of upstream tags to build, with Renovate annotations for automated updates

The CI dynamically detects which images changed and builds all version combinations from `versions.yaml`.

## Adding a New Image

1. Create directory: `mkdir my-image`
2. Create `Containerfile` with `ARG UPSTREAM_TAG` and `FROM base:${UPSTREAM_TAG}`
3. Create `versions.yaml` with Renovate annotation:
   ```yaml
   versions:
     - "1.0.0-tag" # renovate: datasource=docker depName=base-image
   ```

## Local Development

Build an image locally:
```bash
buildah build --build-arg UPSTREAM_TAG=3.2.9-trixie -f haproxy-debian/Containerfile --format=docker
```

Lint a Containerfile:
```bash
hadolint <image-name>/Containerfile
```

## CI/CD Workflows

- **test.yml** (PR): Runs Hadolint on changed Containerfiles
- **build.yml** (main): Builds, pushes to GHCR, signs with Cosign, generates attestations
- **security.yml** (post-build + weekly): Trivy and Kubescape vulnerability scans

## Renovate Configuration

Renovate uses a custom regex manager to update versions in `versions.yaml` files. Only patch updates are auto-enabled for Docker images (major/minor disabled by default).

## Hadolint Configuration

Trusted registries: `docker.io`, `ghcr.io`. See `.hadolint.yaml` for settings.
