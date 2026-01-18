variable "REGISTRY" {
  default = "ghcr.io/wiremind"
}

# See: https://github.com/docker/buildx
variable "BUILDX_VERSIONS" {
  default = ["v0.30.1"]
}

group "default" {
  targets = ["debian13"]
}

target "debian13" {
  name       = "debian13-${replace(v, ".", "-")}"
  matrix     = { v = BUILDX_VERSIONS }
  context    = "."
  dockerfile = "Containerfile.debian13"
  tags       = ["${REGISTRY}/buildx:${v}-debian13"]
  args       = { BUILDX_VERSION = "${v}" }
  platforms  = ["linux/amd64"]
}
