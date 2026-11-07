#!/bin/sh
# Test runner.

source .venv/bin/activate
python3 ./manage.py test --noinput
