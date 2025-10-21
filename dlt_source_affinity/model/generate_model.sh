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

    log "Applying OpenAPI spec patch"
    git apply \
        --allow-empty \
        ./v2_spec_patches.diff
    log "Applied spec patch"

    log "Generating code from OpenAPI spec"
    rm -rf ./v2
    mkdir -p ./v2
    # we need to ignore extra fields because DLT adds extra fields to models like _dlt_id, etc.
    datamodel-codegen \
        --input v2_spec.json \
        --output ./v2 \
        --output-model-type pydantic_v2.BaseModel \
        --use-annotated \
        --use-union-operator \
        --capitalise-enum-members \
        --use-field-description \
        --input-file-type openapi \
        --field-constraints \
        --use-double-quotes \
        --base-class ...MyBaseModel \
        --disable-timestamp \
        --target-python-version "${python_version}" \
        --extra-fields "ignore"
    log "Generated code"
    
    log "Reverting OpenAPI spec patch"
    git checkout \
        ./v2_spec.json
    log "Reverted spec patch"

    log "Applying model patch"
    git apply \
        --allow-empty \
        ./v2_model_patches.diff
    log "Applied model patch"

    popd >/dev/null
}

main "$@"
