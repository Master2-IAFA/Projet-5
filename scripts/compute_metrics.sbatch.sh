#!/bin/bash

#SBATCH --job-name=sharpf-fuse-image-synth
#SBATCH --output=/trinity/home/e.bogomolov/tmp/sharpf_images/%A_%a.out
#SBATCH --error=/trinity/home/e.bogomolov/tmp/sharpf_images/%A_%a.err
#SBATCH --array=1-550
#SBATCH --time=00:10:00
#SBATCH --partition=htc
#SBATCH --cpus-per-task=1
#SBATCH --ntasks=1
#SBATCH --mem-per-cpu=2g
#SBATCH --oversubscribe

__usage="
Usage: $0 [-v] <[input_filename]

  -v:   if set, verbose mode is activated (more output from the script generally)

Example:
  sbatch $( basename "$0" ) -v <inputs.txt
"

usage() { echo "$__usage" >&2; }

# Get all the required options and set the necessary variables
VERBOSE=false
while getopts "v" opt
do
    case ${opt} in
        v) VERBOSE=true;;
        *) usage; exit 1 ;;
    esac
done

if [[ "${VERBOSE}" = true ]]; then
    set -x
    VERBOSE_ARG="--verbose"
fi

# get image filenames from here
PROJECT_ROOT=/trinity/home/e.bogomolov/data_quality
source "${PROJECT_ROOT}"/env.sh

CODE_PATH_CONTAINER="/code"
CODE_PATH_HOST=${PROJECT_ROOT}

echo "******* LAUNCHING IMAGE ${SIMAGE_FILENAME} *******"
echo "  "
echo "  HOST OPTIONS:"
echo "  code path:            ${CODE_PATH_HOST}"
echo "  "
echo "  CONTAINER OPTIONS:"
echo "  code path:            ${CODE_PATH_CONTAINER}"
echo "  "

N_TASKS=${SLURM_NTASKS}
OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK}

COMBINE_SCRIPT="${CODE_PATH_CONTAINER}/scripts/compute_metrics.py"

PARAM_DISTANCE_INTERP_FACTOR=6.0
PARAM_NN_SET_SIZE=8
PARAM_INTERPOLATOR_FUNCTION=bisplrep

# Read SLURM_ARRAY_TASK_ID num lines from standard input,
# stopping at line whole number equals SLURM_ARRAY_TASK_ID
count=0
while IFS=' ' read -r TRUE_FILENAME_GLOBAL PRED_PATH_GLOBAL OUTPUT_PATH_GLOBAL OUT_HTML PARAM_RESOLUTION_3D; do
    (( count++ ))
    if (( count == SLURM_ARRAY_TASK_ID )); then
        break
    fi
done <"${1:-/dev/stdin}"


#SLICE_START=$(( SLICE_SIZE * SLURM_ARRAY_TASK_ID ))
#SLICE_END=$(( SLICE_SIZE * (SLURM_ARRAY_TASK_ID + 1) ))
#echo "SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID} SLICE_START=${SLICE_START} SLICE_END=${SLICE_END}"
#
echo ${OUT_HTML}
singularity exec \
  --bind ${CODE_PATH_HOST}:${CODE_PATH_CONTAINER} \
  --bind "${PWD}":/run/user \
  --bind /gpfs:/gpfs \
  "${SIMAGE_FILENAME}" \
      bash -c 'export OMP_NUM_THREADS='"${OMP_NUM_THREADS}; \\
      python3 ${COMBINE_SCRIPT} \\
        -t ${TRUE_FILENAME_GLOBAL} \\
        -p ${PRED_PATH_GLOBAL} \\
        -o ${OUTPUT_PATH_GLOBAL}/metrics.txt \\
        -r ${PARAM_RESOLUTION_3D} \\
           1> >(tee ${OUTPUT_PATH_GLOBAL}/${SLURM_ARRAY_TASK_ID}.out) \\
           2> >(tee ${OUTPUT_PATH_GLOBAL}/${SLURM_ARRAY_TASK_ID}.err)"
