#!/bin/bash

# DO NOT CHANGE !
export DATA_PATH_CONTAINER=/code/data/abc_test/
export CODE_PATH_CONTAINER=/code
export OUTPUT_PATH_CONTAINER=/code/outputs
export MAKE_DATA_SCRIPT="${CODE_PATH_CONTAINER}/scripts/data_scripts/generate_depthmap_data.py"
export N_TASKS=6
export CONFIGS_PATH="${CODE_PATH_CONTAINER}/scripts/data_scripts/configs/depthmap_datasets"
export DATASET_PATH="${CONFIGS_PATH}/high_res_whole.json"

# Parameters
export SLICE_START=0
export SLICE_END=1
export CHUNK=0
export VERBOSE_ARG="--verbose"

python3 ${MAKE_DATA_SCRIPT} \
    --input-dir ${DATA_PATH_CONTAINER} \
    --chunk ${CHUNK} \
    --output-dir ${OUTPUT_PATH_CONTAINER} \
    --jobs ${N_TASKS} \
    -n1 ${SLICE_START} \
    -n2 ${SLICE_END} \
    --dataset-config ${DATASET_PATH} \
     ${VERBOSE_ARG}
