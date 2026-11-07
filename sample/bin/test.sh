#!/bin/sh
# Tests.

source ./.venv/bin/activate
python3 manage.py test --noinput
