import os
import xml.etree.ElementTree as ET
from io import StringIO

import numpy as np
import trimesh

from sharpf.utils.py_utils.os import change_ext


def load_meshlab_project(meshlab_project_filename):
    """Loads MeshLab .mlp file and gets

    :param meshlab_project_filename:
    :return:
    """
    base_dir = os.path.normpath(
        os.path.dirname(meshlab_project_filename))
    root = ET.parse(meshlab_project_filename).getroot()

    points_by_scan = []
    transform_by_scan_4x4 = {}
    item_id = None
    mesh_transform = None

    for type_tag in root.findall('MeshGroup/MLMesh'):
        filename = type_tag.get('filename')
        if filename.endswith('.obj') or filename.endswith('.stl'):
            item_id = filename
            try:
                mesh_transform = np.loadtxt(
                    StringIO(type_tag.find('MLMatrix44').text))
            except ValueError as e:
                pass

        elif filename.endswith('.ply'):
            # should be like 42side_5.ply or 25_03_sharp_feat_7.ply
            _, scan_index = os.path.basename(change_ext(filename, ''))\
                .rsplit('_', maxsplit=1)
            scan_index = int(scan_index)
            try:
                transform = np.loadtxt(
                    StringIO(type_tag.find('MLMatrix44').text))
                transform_by_scan_4x4[scan_index] = transform
            except ValueError as e:
                pass

            try:
                points = trimesh.load(os.path.join(base_dir, filename)).vertices
                points_by_scan.append(points)
            except ValueError as e:
                pass

    return points_by_scan, transform_by_scan_4x4, item_id, mesh_transform