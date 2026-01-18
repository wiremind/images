variable "REGISTRY" {
  default = "ghcr.io/wiremind"
}

variable "VERSIONS" {
  default = ["1.28.0-alpine", "1.29.3-alpine"]
}

group "default" {
  targets = ["nginx-vts-exporter"]
}

target "nginx-vts-exporter" {
  name       = "nginx-vts-exporter-${replace(replace(v, ".", "-"), "-alpine", "")}"
  matrix     = { v = VERSIONS }
  context    = "."
  dockerfile = "Containerfile"
  tags       = ["${REGISTRY}/nginx-vts-exporter:${v}"]
  args       = { UPSTREAM_TAG = v }
  platforms  = ["linux/amd64"]
}
