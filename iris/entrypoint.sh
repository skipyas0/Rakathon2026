#!/bin/sh
# Volumes mount root-owned (Fly always, Docker on a fresh volume): hand the data directory to
# irisowner, then run IRIS as irisowner through the image's own entrypoint. mkdir: on Fly it's a
# subfolder, since a fresh ext4 volume holds lost+found and IRIS needs an empty directory.
# tini -s: on Fly tini isn't PID 1, so it must register as subreaper to reap zombies.
mkdir -p "$ISC_DATA_DIRECTORY" && chown irisowner:irisowner "$ISC_DATA_DIRECTORY"
exec setpriv --reuid=irisowner --regid=irisowner --init-groups env HOME=/home/irisowner \
  /tini -s -- /iris-main "$@"
