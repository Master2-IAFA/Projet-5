#!/bin/bash

export DATA_PATH=abc_0000_0_1.hdf5
export OUTPUT_PATH=test/abc_0000_0_1
export WEIGHTS_PATH=pretrained_models/def-image-arbitrary-regression-high-0.ckpt

python3 train_net.py \
    trainer.gpus=0 \
    datasets.path=${DATA_PATH} \
    callbacks=regression \
    datasets=unlabeled-image \
    model=unet2d-hist \
    transform=depth-sl-regression-arbitrary \
    system=def-image-regression \
    hydra.run.dir=${OUTPUT_PATH} \
    eval_only=true \
    test_weights=${WEIGHTS_PATH}

