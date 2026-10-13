# Use installed rclone, or its official container with repo-local private config.
media_rclone() {
  if command -v rclone >/dev/null 2>&1; then
    command rclone "$@"
  else
    test -f ./rclone.conf || { echo "Missing private rclone.conf for container mirror" >&2; return 1; }
    docker run --rm --user "$(id -u):$(id -g)" \
      -v "$PWD:$PWD" -w "$PWD" -e "RCLONE_CONFIG=$PWD/rclone.conf" \
      "${RCLONE_IMAGE:-rclone/rclone@sha256:2687085f718d3c628f7fdfb77c52a1d344332aed543110bb88088f2c70d43eb5}" "$@"
  fi
}
