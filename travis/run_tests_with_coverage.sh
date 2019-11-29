#!/bin/bash

# needed for coverage in subprocess
export PYTHONPATH=$PWD

coverage run -p -m pytest --cov=amber_runner

# collect all coverage in root dir
find . -iname '.coverage.*' -exec mv -t $PWD {} +

# generate combined report
coverage combine