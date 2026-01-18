# Wiremind Container Images

Custom container images built and maintained by Wiremind, published to GitHub Container Registry.

## Available Images

| Image | Description | Registry |
| ----- | ----------- | -------- |
| **haproxy** | HAProxy with lua-json for haproxy-ingress auth support | `ghcr.io/wiremind/haproxy` |
| **nginx-vts-exporter** | Nginx with VTS (Virtual host Traffic Status) module | `ghcr.io/wiremind/nginx-vts-exporter` |
| **kubectl** | Kubectl CLI | `ghcr.io/wiremind/kubectl` |
| **buildx** | Docker Buildx CLI | `ghcr.io/wiremind/buildx` |
| **gentoo-stage3** | Gentoo stage3 base image | `ghcr.io/wiremind/gentoo-stage3` |

## Usage

```bash
# Pull an image
docker pull ghcr.io/wiremind/haproxy:3.3.1-debian13

# Use in Dockerfile
FROM ghcr.io/wiremind/haproxy:3.3.1-debian13
```

## Project Structure

```text
├── images/
│   └── <image-name>/
│       ├── docker-bake.hcl       # Bake config (versions, tags, targets)
│       └── Containerfile*        # One or more Containerfiles
├── .github/workflows/
│   ├── bake.yml                  # Build, push, sign with Cosign
│   ├── test.yml                  # PR: Hadolint linting
│   └── security.yml              # Trivy & Kubescape scans
└── renovate.json                 # Automated dependency updates
```

## Adding a New Image

1. Create directory: `mkdir -p images/my-image`

2. Create `docker-bake.hcl`:

   ```hcl
   variable "REGISTRY" {
     default = "ghcr.io/wiremind"
   }

   variable "VERSIONS" {
     default = ["1.0.0", "1.1.0"]
   }

   group "default" {
     targets = ["my-image"]
   }

   target "my-image" {
     name       = "my-image-${replace(v, ".", "-")}"
     matrix     = { v = VERSIONS }
     context    = "."
     dockerfile = "Containerfile"
     tags       = ["${REGISTRY}/my-image:${v}"]
     args       = { UPSTREAM_TAG = v }
     platforms  = ["linux/amd64"]
   }
   ```

3. Create `Containerfile`:

   ```dockerfile
   # syntax=docker.io/docker/dockerfile-upstream:1.20.0
   ARG UPSTREAM_TAG=1.0.0
   FROM docker.io/library/base:${UPSTREAM_TAG}
   # Your customizations
   ```

4. Push to `main` - CI will automatically build and push all versions.

## Local Development

```bash
# Preview what will be built
docker buildx bake -f images/haproxy/docker-bake.hcl --print

# Build locally (no push)
docker buildx bake -f images/haproxy/docker-bake.hcl

# Build and push
docker buildx bake -f images/haproxy/docker-bake.hcl --push

# Lint Containerfiles
hadolint images/my-image/Containerfile
```

## CI/CD Workflows

| Workflow | Trigger | Actions |
| -------- | ------- | ------- |
| **bake.yml** | Push to main | Build changed images, push to GHCR, sign with Cosign |
| **test.yml** | Pull Request | Hadolint linting on changed Containerfiles |
| **security.yml** | After build + weekly | Trivy & Kubescape vulnerability scans |

## Security

All images are:

- **Signed** with [Cosign](https://github.com/sigstore/cosign) using keyless signing
- **Scanned** with [Trivy](https://github.com/aquasecurity/trivy) and [Kubescape](https://github.com/kubescape/kubescape)
- **Reproducible** using `SOURCE_DATE_EPOCH` from git commit timestamps

Results are available in the [Security tab](../../security/code-scanning).

## Dependency Updates

[Renovate](https://github.com/renovatebot/renovate) automatically creates PRs for version updates.

## License

See [LICENSE](LICENSE) file.
