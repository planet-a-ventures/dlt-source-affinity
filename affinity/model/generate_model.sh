#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

log() {
    >&2 echo "$@"
}

main() {

    pushd "${SCRIPT_DIR}" >/dev/null

    local python_version
    python_version=$(./current_python_major_minor.py)

    log "Current Python version: ${python_version}"


    datamodel-codegen \
        --input v2_spec.json \
        --output v2.py \
        --output-model-type pydantic_v2.BaseModel \
        --use-annotated \
        --use-union-operator \
        --capitalise-enum-members \
        --use-field-description \
        --input-file-type openapi \
        --field-constraints \
        --use-double-quotes \
        --base-class ..MyBaseModel \
        --disable-timestamp \
        --target-python-version "${python_version}"

    log "Generated code"

    git apply \
        --allow-empty \
        ./v2_model_patches.diff

    log "Applied patch"

    popd >/dev/null
}

main "$@"
