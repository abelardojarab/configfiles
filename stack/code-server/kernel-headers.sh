#!/bin/sh
# Links the host's kernel headers, mounted read-only at /host/usr/src by
# docker-compose.yml, into /usr/src, where the build links in the host's
# /lib/modules/<version> (mounted at the same path) point, so
#   make -C /lib/modules/$(uname -r)/build M=$PWD
# builds a module for the host's running kernel. The host's /usr/src is
# not mounted over the image's, which holds GoogleTest's sources.
# linuxserver's init runs every script in /custom-cont-init.d as root at
# each container start, so headers of a kernel the host gains are linked
# at the next start.
for dir in /host/usr/src/linux-headers-*; do
  # The pattern stays unexpanded when nothing is mounted there.
  [ -d "$dir" ] || continue
  ln -sfn "$dir" "/usr/src/${dir##*/}"
done
