#!/bin/bash

#SBATCH --job-name=def-plot-snapshots
#SBATCH --output=/trinity/home/a.artemov/tmp/def-plot-snapshots/%A_%a.out
#SBATCH --error=/trinity/home/a.artemov/tmp/def-plot-snapshots/%A_%a.err
#SBATCH --array=1-1
#SBATCH --time=00:10:00
#SBATCH --partition=htc
#SBATCH --cpus-per-task=1
#SBATCH --ntasks=1
#SBATCH --mem-per-cpu=4g
#SBATCH --oversubscribe

__usage="
Usage: $0 [-v] -m method -i input_filename

  -v:   if set, verbose mode is activated (more output from the script generally)
  -m:   method which is used as sub-dir where to read predictions and store output
  -i:   input filename with format FILENAME<space>RESOLUTION_3D

Example:
  sbatch $( basename "$0" ) -v -m def -i inputs.txt
"

usage() { echo "$__usage" >&2; }

# Get all the required options and set the necessary variables
VERBOSE=false
while getopts "vi:m:" opt
do
    case ${opt} in
        v) VERBOSE=true;;
        m) INPUT_FILENAME=$OPTARG;;
        i) METHOD=$OPTARG;;
        *) usage; exit 1 ;;
    esac
done

set -x
if [[ "${VERBOSE}" = true ]]; then
    set -x
    VERBOSE_ARG="--verbose"
fi

# get image filenames from here
PROJECT_ROOT=/trinity/home/a.artemov/repos/sharp_features2
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

OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK}

SNAPSHOT_SCRIPT="${CODE_PATH_CONTAINER}/scripts/plot_snapshots.py"

POINT_SIZE=1.1
POINT_SHADER=flat
# Read SLURM_ARRAY_TASK_ID num lines from standard input,
# stopping at line whole number equals SLURM_ARRAY_TASK_ID
count=0
while IFS=' ' read -r source_filename resolution_3d; do
    (( count++ ))
    if (( count == SLURM_ARRAY_TASK_ID )); then
        break
    fi
done <"${INPUT_FILENAME:-/dev/stdin}"

INPUT_BASE_DIR=/gpfs/gpfs0/3ddl/sharp_features/data_v2_cvpr
FUSION_BASE_DIR=/gpfs/gpfs0/3ddl/sharp_features/whole_fused/data_v2_cvpr
output_path_global="${FUSION_BASE_DIR}/$( realpath --relative-to  ${INPUT_BASE_DIR} "${source_filename%.*}" )/${METHOD}"

fused_gt="${output_path_global}/$( basename "${source_filename}" .hdf5)__ground_truth.hdf5"

fused_pred_min="${output_path_global}/$( basename "${source_filename}" .hdf5)__min.hdf5"
fused_pred_min_absdiff="${output_path_global}/$( basename "${source_filename}" .hdf5)__min__absdiff.hdf5"

fused_pred_adv60="${output_path_global}/$( basename "${source_filename}" .hdf5)__adv60__min.hdf5"
fused_pred_adv60_absdiff="${output_path_global}/$( basename "${source_filename}" .hdf5)__adv60__absdiff.hdf5"

fused_pred_linreg="${output_path_global}/$( basename "${source_filename}" .hdf5)__crop__linreg.hdf5"
fused_pred_linreg_absdiff="${output_path_global}/$( basename "${source_filename}" .hdf5)__linreg__absdiff.hdf5"

fused_snapshot="${output_path_global}/$( basename "${source_filename}" .hdf5).html"

input_arg="-i ${fused_gt}"
icm_arg="-icm plasma_r"
if [[ -f ${fused_pred_min} ]]
then
  input_arg="${input_arg} -i ${fused_pred_min} -i ${fused_pred_min_absdiff}"
  icm_arg="${icm_arg} -icm plasma_r -icm plasma"
fi

if [[ -f ${fused_pred_adv60} ]]
then
  input_arg="${input_arg} -i ${fused_pred_adv60} -i ${fused_pred_adv60_absdiff}"
  icm_arg="${icm_arg} -icm plasma_r -icm plasma"
fi

if [[ -f ${fused_pred_linreg} ]]
then
  input_arg="${input_arg} -i ${fused_pred_linreg} -i ${fused_pred_linreg_absdiff}"
  icm_arg="${icm_arg} -icm plasma_r -icm plasma"
fi

singularity exec \
  --bind ${CODE_PATH_HOST}:${CODE_PATH_CONTAINER} \
  --bind "${PWD}":/run/user \
  --bind /gpfs:/gpfs \
  "${SIMAGE_FILENAME}" \
      bash -c 'export OMP_NUM_THREADS='"${OMP_NUM_THREADS}; \\
      python3 ${SNAPSHOT_SCRIPT} \\
        ${input_arg} \\
        ${icm_arg} \\
        -s ${POINT_SIZE} \\
        -ps ${resolution_3d} \\
        -ph ${POINT_SHADER} \\
        --output ${fused_snapshot} \\
        ${VERBOSE_ARG} \\
           1> >(tee ${output_path_global}/${SLURM_ARRAY_TASK_ID}.out) \\
           2> >(tee ${output_path_global}/${SLURM_ARRAY_TASK_ID}.err)"