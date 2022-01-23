#!/bin/bash

#SBATCH --job-name=sharpf-stats
#SBATCH --output=/trinity/home/a.artemov/tmp/sharpf-stats/%A.out
#SBATCH --error=/trinity/home/a.artemov/tmp/sharpf-stats/%A.err
#SBATCH --time=24:00:00
#SBATCH --partition=htc
#SBATCH --cpus-per-task=10
#SBATCH --ntasks=1
#SBATCH --mem-per-cpu=6g

__usage="
Usage: $0 -a abc_input_dir -o output_file [-v]

  -a: 	input ABC directory
  -c: 	input ABC chunk number
  -o: 	output file with resulting output
  -v:   if set, verbose mode is activated (more output from the script generally)
"

usage() { echo "$__usage" >&2; }

# Get all the required options and set the necessary variables
VERBOSE=false
while getopts "a:c:o:v" opt
do
    case ${opt} in
        c) CHUNK=$OPTARG;;
        a) ABC_PATH_HOST=$OPTARG;;
        o) OUTPUT_FILE_HOST=$OPTARG;;
        v) VERBOSE=true;;
        *) usage; exit 1 ;;
    esac
done

if [[ "${VERBOSE}" = true ]]; then
    set -x
    VERBOSE_ARG="--verbose"
fi

# get image filenames from here
PROJECT_ROOT=/trinity/home/a.artemov/repos/sharp_features2
source "${PROJECT_ROOT}"/env.sh

ABC_PATH_CONTAINER="/abc"
if [[ ! ${ABC_PATH_HOST} ]]; then
    echo "input_dir is not set" && usage && exit 1
fi

OUTPUT_PATH_CONTAINER="/out"
if [[ ! ${OUTPUT_FILE_HOST} ]]; then
    echo "output_dir is not set" && usage && exit 1
fi
OUTPUT_PATH_HOST=$( dirname "${OUTPUT_FILE_HOST}" )
OUTPUT_BASENAME=$( basename "${OUTPUT_FILE_HOST}" )

CODE_PATH_CONTAINER="/code"
CODE_PATH_HOST=${PROJECT_ROOT}

echo "******* LAUNCHING IMAGE ${SIMAGE_FILENAME} *******"
echo "  "
echo "  HOST OPTIONS:"
echo "  code path:            ${CODE_PATH_HOST}"
echo "  abc path:             ${ABC_PATH_HOST}"
echo "  output path:          ${OUTPUT_PATH_HOST}"
echo "  "
echo "  CONTAINER OPTIONS:"
echo "  code path:            ${CODE_PATH_CONTAINER}"
echo "  abc path:             ${ABC_PATH_CONTAINER}"
echo "  output path:          ${OUTPUT_PATH_CONTAINER}"
echo "  "

N_TASKS=$(( SLURM_CPUS_PER_TASK ))
SCRIPT="${CODE_PATH_CONTAINER}/scripts/data_scripts/compute_abcchunk_statistics.py"
OUTPUT_FILE="${OUTPUT_PATH_CONTAINER}/${OUTPUT_BASENAME}"

singularity exec \
  --bind ${CODE_PATH_HOST}:${CODE_PATH_CONTAINER} \
  --bind "${ABC_PATH_HOST}":${ABC_PATH_CONTAINER} \
  --bind "${OUTPUT_PATH_HOST}":${OUTPUT_PATH_CONTAINER} \
  --bind "${PWD}":/run/user \
  "${SIMAGE_FILENAME}" \
      bash -c 'export OMP_NUM_THREADS='"${SLURM_CPUS_PER_TASK}; \\
      python3 ${SCRIPT} \\
        --chunk ${CHUNK} \\
        --abc-input-dir ${ABC_PATH_CONTAINER} \\
        --output-file ${OUTPUT_FILE} \\
        --jobs ${N_TASKS} \\
        ${VERBOSE_ARG} \\
        "