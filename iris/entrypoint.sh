#!/bin/sh
# Volumes mount root-owned (Fly always, Docker on a fresh volume): hand the data directory to
# irisowner, then run IRIS as irisowner through the image's own entrypoint.
chown irisowner:irisowner "$ISC_DATA_DIRECTORY"
exec setpriv --reuid=irisowner --regid=irisowner --init-groups env HOME=/home/irisowner \
  /tini -- /iris-main "$@"
