#!/bin/bash

fuse_script="/code/scripts/fusion/fuse_images_synthetic.py"

shape="abc_test_3_4"
views_gt="/code/data/${shape}.hdf5"
views_pred_dir="/code/sharpf/neural/test/${shape}/predictions/"
output_path="/code/outputs/${shape}/"

N_JOBS=6
PARAM_RESOLUTION_3D=0.02
PARAM_DISTANCE_INTERP_FACTOR=6.0
PARAM_NN_SET_SIZE=8
PARAM_INTERPOLATOR_FUNCTION=bisplrep

python3 ${fuse_script} \
    --true-filename ${views_gt} \
    --pred-dir ${views_pred_dir} \
    --output-dir ${output_path} \
    --jobs ${N_JOBS} \
    --nn_set_size ${PARAM_NN_SET_SIZE} \
    --resolution_3d ${PARAM_RESOLUTION_3D} \
    --distance_interp_factor ${PARAM_DISTANCE_INTERP_FACTOR} \
    --interpolator_function ${PARAM_INTERPOLATOR_FUNCTION}
