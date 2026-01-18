variable "REGISTRY" {
  default = "ghcr.io/wiremind"
}

// Gentoo stage3 profiles (e.g., "hardened-systemd", "musl-hardened")
variable "PROFILES" {
  default = ["hardened-systemd", "musl-hardened"]
}

// Stage3 timestamp (update when new releases are available)
variable "TIMESTAMP" {
  default = "20260111T160052Z"
}

group "default" {
  targets = ["stage3"]
}

target "stage3" {
  name       = "${replace(v, "-", "_")}"
  matrix     = { v = PROFILES }
  context    = "."
  dockerfile = "Containerfile"
  tags       = ["${REGISTRY}/gentoo-stage3:${v}"]
  args       = {
    UPSTREAM_TAG = v
    TIMESTAMP    = TIMESTAMP
  }
  platforms  = ["linux/amd64"]
}
