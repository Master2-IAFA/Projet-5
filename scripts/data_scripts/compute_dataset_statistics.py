#!/usr/bin/env python3

import argparse
import json
import os
import sys
from functools import partial
from typing import Mapping, List

import numpy as np
import yaml
from torch.utils.data import DataLoader

__dir__ = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '..', '..')
)
sys.path[1:1] = [__dir__]

from sharpf.data.imaging import IMAGING_BY_TYPE
import sharpf.data.datasets.sharpf_io as io
from sharpf.utils.geometry_utils.geometry import mean_mmd
from sharpf.utils.py_utils.config import load_func_from_config
from sharpf.utils.abc_utils.abc.abc_data import ABCChunk, ABC_7Z_FILEMASK, ABCModality
from sharpf.utils.abc_utils.abc.feature_utils import compute_features_nbhood, remove_boundary_features
from sharpf.utils.abc_utils.mesh.indexing import reindex_zerobased
from sharpf.utils.abc_utils.mesh.io import trimesh_load
from sharpf.utils.py_utils.console import eprint_t
from sharpf.utils.abc_utils.hdf5.dataset import Hdf5File, PreloadTypes
from sharpf.utils.abc_utils.hdf5.io_struct import collate_mapping_with_io


PATCH_TYPES = ['plane', 'cylinder', 'cone', 'sphere', 'torus', 'revolution', 'extrusion', 'bspline', 'other']
CURVE_TYPES = ['line', 'circle', 'ellipse', 'bspline', 'other']


def uncollate(collated: Mapping) -> List[Mapping]:
    """
    Given a collated batch (i.e., a mapping of lists/arrays),
    produce a list of mappings.
    """
    any_value = next(iter(collated.values()))
    list_len = len(any_value)
    return [
        {key: value[idx] for key, value in collated.items()}
        for idx in range(list_len)
    ]


def process_images(
        item,
        imaging,
        obj_filename,
        feat_filename
):
    mesh_vertex_indexes = item['orig_vert_indices']
    mesh_face_indexes = item['orig_face_indexes']

    with ABCChunk([obj_filename, feat_filename]) as data_holder:
        abc_item = data_holder.get(str(item['item_id'].decode('utf-8')))
        mesh, _, _ = trimesh_load(abc_item.obj)
        features = yaml.load(abc_item.feat, Loader=yaml.Loader)

    nbhood = reindex_zerobased(mesh, mesh_vertex_indexes, mesh_face_indexes)
    nbhood_features = compute_features_nbhood(mesh, features, mesh_vertex_indexes, mesh_face_indexes)
    nbhood_features = remove_boundary_features(nbhood, nbhood_features, how='edges')

    points = imaging.image_to_points(item["image"])
    s = [
        f'has_sharp {int(item["has_sharp"])}',
        f'num_sharp_curves {item["num_sharp_curves"]}',
        f'num_surfaces {item["num_surfaces"]}',
        f'num_samples {int(np.count_nonzero(item["image"]))}'
        f'mean_sampling_distance {mean_mmd(points)}'
    ]

    for curve_type in CURVE_TYPES:
        count = len([curve for curve in nbhood_features['curves'] if curve['type'] == curve_type])
        s.append(f'num_curve_{curve_type} {count}')

    for surface_type in PATCH_TYPES:
        count = len([surface for surface in nbhood_features['surfaces'] if surface['type'] == surface_type])
        s.append(f'num_surface_{surface_type} {count}')

    return s


def main(options):
    # % \LA{for submission -- add figures displaying:
    # % 1) distribution of types of patches and curves over the patch-based dataset;
    # % 2) distribution of the number of patches and curves over the patch-based dataset;
    # % 3) empirical histogram of sampling density;
    # % 4) statistics about which percentage of surface is captured;
    # % 5) empirical histogram of number of points in scan}

    schema = io.IO_SPECS[options.io_spec]
    process_fn = {
        'images': process_images,
    }[options.io_spec]

    batch_size = 128
    loader = DataLoader(
        Hdf5File(
            options.input_file,
            io=schema,
            labels='*',
            preload=PreloadTypes.NEVER),
        num_workers=options.n_jobs,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=partial(collate_mapping_with_io, io=schema))

    with open(options.dataset_config) as config_file:
        config = json.load(config_file)
    imaging = load_func_from_config(IMAGING_BY_TYPE, config['imaging'])

    obj_filename = os.path.join(
        options.abc_input_dir,
        ABC_7Z_FILEMASK.format(
            chunk=options.chunk.zfill(4),
            modality=ABCModality.OBJ.value,
            version='00'))
    feat_filename = os.path.join(
        options.abc_input_dir,
        ABC_7Z_FILEMASK.format(
            chunk=options.chunk.zfill(4),
            modality=ABCModality.FEAT.value,
            version='00'))
    if options.verbose:
        eprint_t('Obj filename: {}, feat filename: {}'.format(obj_filename, feat_filename))

    stored_count = 0
    for batch_idx, batch in enumerate(loader):
        items = uncollate(batch)

        for item in items:
            try:
                s = process_fn(item, imaging, obj_filename, feat_filename)
            except Exception as e:
                if options.verbose:
                    eprint_t('Error getting item {}: {}'.format(item['item_id'], str(e)))
                continue

            with open(options.output_file, 'a') as out_file:
                out_file.write('\n'.join(s) + '\n')

        if options.verbose:
            any_key = next(items[0].keys())
            stored_count += len(items[0][any_key])
            seen_fraction = batch_idx * batch_size / len(loader.dataset)
            eprint_t('Processed {0:d} items ({1:3.1f}% of data), stored {2:d} items'.format(
                batch_idx * batch_size, seen_fraction * 100, stored_count))


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input-file', dest='input_file',
                        required=True, help='input HDF5 file.')
    parser.add_argument('-a', '--abc-input-dir', dest='abc_input_dir',
                        required=True, help='input dir with ABC dataset.')
    parser.add_argument('-c', '--chunk', required=True, help='ABC chunk id to process.')
    parser.add_argument('-o', '--output-file', dest='output_file',
                        required=True, help='output file.')
    parser.add_argument('-g', '--dataset-config', dest='dataset_config',
                        required=True, help='dataset configuration file.')
    parser.add_argument('-j', '--jobs', dest='n_jobs',
                        type=int, default=4, help='CPU jobs to use in parallel [default: 4].')
    parser.add_argument('-io', '--io-schema', dest='io_spec',
                        choices=io.IO_SPECS.keys(), help='i/o spec to use.')

    parser.add_argument('--verbose', dest='verbose', action='store_true', default=False,
                        required=False, help='be verbose')
    return parser.parse_args()


if __name__ == '__main__':
    options = parse_args()
    main(options)