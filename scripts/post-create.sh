#!/usr/bin/env bash
# requirements_dev is already loaded by Dockerfile.dev
# pip3 install -r requirements_dev.txt
source .venv/bin/activate
pip show pymodbus
