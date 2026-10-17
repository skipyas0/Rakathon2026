#!/bin/bash
# Runs once IRIS is up. Idempotent: setup.script skips an existing endpoint.
iris session IRIS < /home/irisowner/setup.script
