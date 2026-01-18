variable "REGISTRY" {
  default = "ghcr.io/wiremind"
}

// kubectl versions (e.g., "v1.34.3", "v1.35.0")
variable "DEBIAN_VERSIONS" {
  default = ["v1.34.3", "v1.35.0"]
}

group "default" {
  targets = ["debian13", "debian13-hardened"]
}

target "debian13" {
  name       = "debian13-${replace(replace(v, ".", "-"), "v", "")}"
  matrix     = { v = DEBIAN_VERSIONS }
  context    = "."
  dockerfile = "Containerfile.debian13"
  tags       = ["${REGISTRY}/kubectl:${v}-debian13"]
  args       = { UPSTREAM_TAG = v }
  platforms  = ["linux/amd64"]
}

target "debian13-hardened" {
  name       = "debian13-hardened-${replace(replace(v, ".", "-"), "v", "")}"
  matrix     = { v = DEBIAN_VERSIONS }
  context    = "."
  dockerfile = "Containerfile.debian13-hardened"
  tags       = ["${REGISTRY}/kubectl:${v}-debian13-hardened"]
  args       = { UPSTREAM_TAG = v }
  platforms  = ["linux/amd64"]
}