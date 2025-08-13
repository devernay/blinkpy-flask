#!/bin/bash
# Helper script to run commands with the correct PYTHONPATH for blinkpy
export PYTHONPATH="/Users/deverf/Documents/third_party/blinkpy-flask/blinkpy:$PYTHONPATH"
exec "$@"
