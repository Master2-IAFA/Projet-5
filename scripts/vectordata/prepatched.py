from glob import iglob
import os

from vectran.data import LineDrawingsDataset
from vectran.data.graphics_primitives import PrimitiveType
from vectran.data.graphics.graphics import VectorImage


def patch_path_pattern(root, basename, patch_size, origin, width='def', orientation='def', rotation=0, t=(0,0)):
    return os.path.join(root, basename, '{}x{}'.format(*patch_size), 'width_{}'.format(width), 'orientation_{}'.format(orientation), 'rotated_deg_{}'.format(rotation), 'translated_{}_{}'.format(*t), '{}_{}.svg'.format(*origin))


class PrepatchedSVG(LineDrawingsDataset):
    def __init__(self, *, data_root, patch_size, widths=('*',), orientations=('*',), rotations=('*',), translations=(('*', '*'),), **kwargs):
        super().__init__(patch_size=patch_size, **kwargs)

        # check that primitive types are compatible with SVG datasets
        if not set(self.primitive_types).issubset(set([PrimitiveType.PT_LINE, PrimitiveType.PT_BEZIER])):
            raise NotImplementedError('SVG datasets do not support primitives other than Lines and Bezier curves')

        # set max primitive number to zero for unneded primitive types
        for primitive_type in PrimitiveType.PT_LINE, PrimitiveType.PT_BEZIER:
            if primitive_type not in self.primitive_types:
                self.max_primitives[primitive_type] = 0

        # collect patch paths
        self.source_images = list(set(path for width in widths for orientation in orientations for rotation in rotations for t in translations for path in iglob(patch_path_pattern(data_root, basename='**', patch_size=patch_size, origin=('*', '*'), width=width, orientation=orientation, rotation=rotation, t=t), recursive=True)))


    def _get_vector_item(self, idx):
        file = self.source_images[idx]
        lines, beziers = VectorImage.from_svg(file).vahe_representation(max_lines_n=self.max_primitives[PrimitiveType.PT_LINE], max_beziers_n=self.max_primitives[PrimitiveType.PT_BEZIER], random_sampling=self.sample_primitives_randomly)

        parameter_sets = {}
        if PrimitiveType.PT_LINE in self.primitive_types:
            parameter_sets[PrimitiveType.PT_LINE] = lines
        if PrimitiveType.PT_BEZIER in self.primitive_types:
            parameter_sets[PrimitiveType.PT_BEZIER] = beziers

        return parameter_sets


    def __len__(self):
        return len(self.source_images)
