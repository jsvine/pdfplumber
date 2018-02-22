#!/bin/sh
set -e
cd examples/notebooks && find . -type f \
    -name "*.ipynb" \
    -not -path "*.ipynb_checkpoints*" \
    -exec jupyter nbconvert \
        --to notebook \
        --ExecutePreprocessor.timeout=-1 \
        --ExecutePreprocessor.kernel_name=python3 \
        --execute {} \
        --output {} \;
