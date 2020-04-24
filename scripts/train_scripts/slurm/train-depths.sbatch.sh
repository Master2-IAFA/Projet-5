#!/bin/bash

#SBATCH --job-name=sharpf-train-depths
#SBATCH --output=logs/sharpf-train-depths_%A_%a.out
#SBATCH --error=logs/sharpf-train-depths_%A_%a.err
#SBATCH --array=1-1
#SBATCH --time=00:10:00
#SBATCH --partition=gpu_debug
#SBATCH --cpus-per-task=4
#SBATCH --gpus=1
#SBATCH --ntasks=1
#SBATCH --mem=40000

module load apps/singularity-3.2.0

__usage="
Usage: $0 -d data_dir -o output_dir -l logs_dir -f model_config [-v]

  -d: 	input data directory
  -o: 	output directory where model weights get written
  -l:   logs directory
  -f:   model config file (from sharpf/models/specs dir)
  -v:   if set, verbose mode is activated (more output from the script generally)

Example:
sbatch make_patches.sbatch.sh
  -d /gpfs/gpfs0/3ddl/datasets/abc \\
  -o /gpfs/gpfs0/3ddl/datasets/abc/eccv  \\
  -l /home/artonson/tmp/logs  \\
  -v
"

usage() { echo "$__usage" >&2; }

# Get all the required options and set the necessary variables
VERBOSE=false
while getopts "c:o:d:l:f:v" opt
do
    case ${opt} in
        o) OUTPUT_PATH_HOST=$OPTARG;;
        d) DATA_PATH_HOST=$OPTARG;;
        l) LOGS_PATH_HOST=$OPTARG;;
        f) MODEL_CONFIG=$OPTARG;;
        v) VERBOSE=true;;
        *) usage; exit 1 ;;
    esac
done

if [[ "${VERBOSE}" = true ]]; then
    set -x
    VERBOSE_ARG="--verbose"
fi

# get image filenames from here
PROJECT_ROOT=/trinity/home/a.artemov/repos/sharp_features
source "${PROJECT_ROOT}"/env.sh

DATA_PATH_CONTAINER="/data"
if [[ ! ${DATA_PATH_HOST} ]]; then
    echo "data_dir is not set" && usage && exit 1
fi

OUTPUT_PATH_CONTAINER="/out"
if [[ ! ${OUTPUT_PATH_HOST} ]]; then
    echo "output_dir is not set" && usage && exit 1
fi

LOGS_PATH_CONTAINER="/logs"
if [[ ! ${LOGS_PATH_HOST} ]]; then
    echo "logs_dir is not set" && usage && exit 1
fi

if [[ ! ${MODEL_CONFIG} ]]; then
    echo "config_file is not set" && usage && exit 1
fi

CODE_PATH_CONTAINER="/code"
CODE_PATH_HOST=${PROJECT_ROOT}

SIMAGE_FILENAME=/gpfs/gpfs0/3ddl/singularity-images/artonson_sharp_features_pointweb-ops.sif

echo "******* LAUNCHING IMAGE ${SIMAGE_FILENAME} *******"
echo "  "
echo "  HOST OPTIONS:"
echo "  data path:            ${DATA_PATH_HOST}"
echo "  code path:            ${CODE_PATH_HOST}"
echo "  logs path:            ${LOGS_PATH_HOST}"
echo "  output path:          ${OUTPUT_PATH_HOST}"
echo "  "
echo "  CONTAINER OPTIONS:"
echo "  data path:            ${DATA_PATH_CONTAINER}"
echo "  code path:            ${CODE_PATH_CONTAINER}"
echo "  logs path:            ${LOGS_PATH_CONTAINER}"
echo "  output path:          ${OUTPUT_PATH_CONTAINER}"
echo "  "

echo "SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID}"

N_TASKS=1
OMP_NUM_THREADS=4
TRAIN_SCRIPT="${CODE_PATH_CONTAINER}/scripts/train_scripts/train_sharp.py"
MODEL_CONFIGS_PATH_CONTAINER="${CODE_PATH_CONTAINER}/sharpf/models/specs"
MODEL_SPEC_PATH="${MODEL_CONFIGS_PATH_CONTAINER}/${MODEL_CONFIG}"
GPU_ID=0
NUM_EPOCHS=10
LOSS_FUNCTION=regress_sharpdf
TRAIN_BATCH_SIZE=16
VAL_BATCH_SIZE=16
LEARNING_RATE=0.001
#SAVE_MODEL_FILEPREFIX=${LOGS_PATH_CONTAINER}/${MODEL_CONFIG}_weights
LOGS_PREFIX="${LOGS_PATH_CONTAINER}/${MODEL_CONFIG}_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}"

singularity exec \
  --nv \
  --bind ${CODE_PATH_HOST}:${CODE_PATH_CONTAINER} \
  --bind ${DATA_PATH_HOST}:${DATA_PATH_CONTAINER} \
  --bind ${LOGS_PATH_HOST}:${LOGS_PATH_CONTAINER} \
  --bind ${OUTPUT_PATH_HOST}:${OUTPUT_PATH_CONTAINER} \
  --bind /gpfs:/gpfs \
  --bind "${PWD}":/run/user \
  "${SIMAGE_FILENAME}" \
      bash -c 'export OMP_NUM_THREADS='"${OMP_NUM_THREADS}; \\
      python3 ${TRAIN_SCRIPT} \\
        --gpu ${GPU_ID} \\
        --model-spec ${MODEL_SPEC_PATH} \\
        --epochs ${NUM_EPOCHS} \\
        --log-dir-prefix ${LOGS_PREFIX} \\
        --loss-funct ${LOSS_FUNCTION} \\
        --train-batch-size ${TRAIN_BATCH_SIZE} \\
        --val-batch-size ${VAL_BATCH_SIZE} \\
        --lr ${LEARNING_RATE} \\
        --data-root ${DATA_PATH_CONTAINER} "

