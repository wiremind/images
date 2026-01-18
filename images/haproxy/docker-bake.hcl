variable "REGISTRY" {
  default = "ghcr.io/wiremind"
}

// Debian versions (HAProxy version only, e.g., "2.8.18", "3.0.14")
variable "DEBIAN_VERSIONS" {
  default = ["2.8.18", "3.0.14", "3.2.10", "3.3.1"]
}

group "default" {
  targets = ["debian13", "debian13-hardened"]
}

target "debian13" {
  name       = "debian13-${replace(v, ".", "-")}"
  matrix     = { v = DEBIAN_VERSIONS }
  context    = "."
  dockerfile = "Containerfile.debian13"
  tags       = ["${REGISTRY}/haproxy:${v}-debian13"]
  args       = { UPSTREAM_TAG = "${v}-trixie" }
  platforms  = ["linux/amd64"]
}

target "debian13-hardened" {
  name       = "debian13-hardened-${replace(v, ".", "-")}"
  matrix     = { v = DEBIAN_VERSIONS }
  context    = "."
  dockerfile = "Containerfile.debian13-hardened"
  tags       = ["${REGISTRY}/haproxy:${v}-debian13-hardened"]
  args       = { UPSTREAM_TAG = "${v}-debian13" }
  platforms  = ["linux/amd64"]
}