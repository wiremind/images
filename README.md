# Wiremind Container Images

Custom & opensource container images built and maintained by Wiremind, published to GitHub Container Registry (ghcr.io).

## Available Images

| Image | Description | Registry |
|-------|-------------|----------|
| **haproxy** | HAProxy with lua-json for haproxy-ingress auth support | `ghcr.io/wiremind/haproxy` |
| **nginx-vts-exporter** | Nginx with VTS (Virtual host Traffic Status) module | `ghcr.io/wiremind/nginx-vts-exporter` |

## Usage

```bash
# Pull an image
docker pull ghcr.io/wiremind/haproxy:3.2.9-trixie
docker pull ghcr.io/wiremind/nginx-vts-exporter:1.28.0-alpine

# Use in Dockerfile
FROM ghcr.io/wiremind/haproxy:3.2.9-trixie
```

## Available Tags

Each image supports multiple versions. Check the `versions.yaml` file in each image directory for available tags.

### HAProxy
- `3.3.0-trixie`, `3.2.9-trixie`, `3.1.10-trixie`, `3.0.12-trixie`, `2.8.16-trixie`

### Nginx VTS Exporter
- `1.28.0-alpine`

## Project Structure

```
├── <image-name>/
│   ├── Containerfile      # Container build instructions
│   └── versions.yaml      # Upstream versions to build
├── .github/workflows/
│   ├── test.yml           # PR: Hadolint linting
│   ├── build.yml          # Main: Build, push, attest
│   └── security.yml       # Main: Trivy & Kubescape scans
└── renovate.json          # Automated dependency updates
```

## Adding a New Image

1. Create a new directory with your image name:
   ```bash
   mkdir my-image
   ```

2. Create a `Containerfile` using `UPSTREAM_TAG` for the base image:
   ```dockerfile
   # syntax=docker/dockerfile:1.12.0
   ARG UPSTREAM_TAG
   FROM some-base-image:${UPSTREAM_TAG}
   
   # Your customizations here
   ```

3. Create a `versions.yaml` with the upstream tags to build:
   ```yaml
   versions:
     - "1.0.0-alpine" # renovate: datasource=docker depName=some-base-image
   ```

4. Commit and push to `main` - the CI will automatically build and push all versions.

## CI/CD Workflows

| Workflow | Trigger | Actions |
|----------|---------|---------|
| **test.yml** | Pull Request | Hadolint linting on changed Containerfiles |
| **build.yml** | Push to main | Build, push to GHCR, generate attestations |
| **security.yml** | After build + weekly | Trivy & Kubescape vulnerability scans |

### Security Scanning

All images are scanned with:
- **[Trivy](https://github.com/aquasecurity/trivy)** - CVE detection in OS packages and libraries
- **[Kubescape](https://github.com/kubescape/kubescape)** - Container security best practices

Results are available in the [Security tab](../../security/code-scanning).

## Dependency Updates

[Renovate](https://github.com/renovatebot/renovate) automatically creates PRs when:
- Upstream base image versions are updated
- GitHub Actions versions are updated

## License

See [LICENSE](LICENSE) file.
