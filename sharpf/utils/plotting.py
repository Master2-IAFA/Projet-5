import copy
from base64 import b64decode

import k3d
import numpy as np
from IPython.display import Image
import randomcolor


def display_sharpness(mesh=None, mesh_color=0xbbbbbb,
                      plot_meshvert=True, meshvert_color=0x666666, meshvert_psize=0.0025,
                      samples=None, samples_distances=None, samples_color=0x0000ff, samples_psize=0.002,
                      sharp_vert=None, sharpvert_color=0xff0000, sharpvert_psize=0.0025,
                      sharp_curves=None, sharpcurve_color=None, sharpcurve_width=0.0025,
                      directions=None, directions_width=0.0025,
                      as_image=False, plot_height=768,
                      point_shader='3d'):
    """A method for plotting the sharp curves on top of the mesh.
    Use it to display meshes, point clouds, distance or direction fields
    along with ground-truth curve annotations.

    :param mesh: the mesh to display (ideally trimesh.Trimesh but namedtuple
                with `vertices` and `faces` attributes should work, too).
                Set to None to turn mesh display off.
    :type mesh: trimesh.Trimesh

    :param mesh_color: the hex color of the mesh to plot
    :type mesh_color: int

    :param plot_meshvert: if True, displays mesh vertices as points of given radius/color
    :type plot_meshvert: bool

    :param meshvert_color: the hex color of the mesh vertices to plot
    :type meshvert_color: int

    :param meshvert_psize: size of mesh vertices
    :type meshvert_psize: float

    :param samples:
    :param samples_color:
    :param samples_psize:
    :type samples:
    :type samples_color:
    :type samples_psize:

    :param samples_distances:

    :param sharp_vert:
    :param sharpvert_color:
    :param sharpvert_psize:

    :param sharp_curves:
    :param sharpcurve_color:
    :param sharpcurve_width:

    :param directions:
    :param directions_width:
    :param as_image:
    :param plot_height:

    :return:

    Usage examples
    ==============
    >>>
    with ABCChunk(['/data/abc_0056_obj_v00.7z', '/data/abc_0056_feat_v00.7z']) as data_holder:
    item = data_holder[100]

    mesh = trimesh_load(item.obj)
    features = yaml.load(item.feat, Loader=yaml.Loader)

    display_sharpness(mesh=mesh,
    """
    plot = k3d.plot(height=plot_height)

    if None is not mesh:
        plot += k3d.mesh(mesh.vertices, mesh.faces,
                         color=mesh_color)

        if plot_meshvert:
            plot += k3d.points(mesh.vertices,
                               point_size=meshvert_psize, color=meshvert_color, shader=point_shader)

    if None is not samples:
        colors = None
        if None is not samples_distances:
            max_dist = np.max(samples_distances)

            colors = k3d.helpers.map_colors(
                samples_distances, k3d.colormaps.basic_color_maps.WarmCool, [0, max_dist]
            ).astype(np.uint32)
            k3d_points = k3d.points(samples, point_size=samples_psize, colors=colors)
        else:
            k3d_points = k3d.points(samples, point_size=samples_psize, color=samples_color)
        plot += k3d_points
        k3d_points.shader = '3d'

        if None is not directions:
            directions_to_plot = np.hstack((samples, samples + directions))

            for i, dir_to_plot in enumerate(directions_to_plot):
                dir_to_plot = dir_to_plot.reshape((2, 3))
                if np.all(dir_to_plot[0] == dir_to_plot[1]):
                    continue
                color = int(colors[i]) if None is not colors else samples_color
                plt_line = k3d.line(dir_to_plot,
                                    shader='mesh', width=directions_width, color=color)
                plot += plt_line

    if None is not sharp_vert:
        k3d_points = k3d.points(sharp_vert,
                                point_size=sharpvert_psize, color=sharpvert_color)
        plot += k3d_points
        k3d_points.shader = '3d'

        if None is not sharp_curves:
            rand_color = randomcolor.RandomColor()
            for i, vert_ind in sharp_curves.items():
                sharp_points_curve = mesh.vertices[vert_ind]
                if None is not sharpcurve_color:
                    color = sharpcurve_color
                else:
                    color = rand_color.generate(hue='red')[0]
                    color = int('0x' + color[1:], 16)
                plt_line = k3d.line(sharp_points_curve,
                                    shader='mesh', width=sharpcurve_width, color=color)
                plot += plt_line

    plot.grid_visible = False
    plot.display()

    if as_image:
        plot.fetch_screenshot()
        return Image(data=b64decode(plot.screenshot))


def display_depth_sharpness(
        depth_images=None,
        sharpness_images=None,
        axes_size=(8, 8),
        ncols=1,
        max_sharpness=1.0,
):
    import matplotlib.cm
    import matplotlib.pyplot as plt

    def fix_chw_array(image_array):
        if None is not image_array:
            image_array = np.asanyarray(image_array).copy()
            assert len(image_array.shape) in [2, 3], "Don't understand the datatype with shape {}".format(
                image_array.shape)
            if len(image_array.shape) == 2:
                image_array = image_array[np.newaxis, ...]
        return image_array

    depth_images = fix_chw_array(depth_images)
    sharpness_images = fix_chw_array(sharpness_images)

    if None is not depth_images and None is not sharpness_images:
        assert len(depth_images) == len(sharpness_images), 'depth and sharpness images dont coincide by length'
        n_images = len(depth_images)
        ncols, nrows, series = 2 * ncols, n_images // ncols, 2

        axes_size = axes_size[0] * ncols, axes_size[1] * nrows
        _, axs = plt.subplots(figsize=axes_size, nrows=nrows, ncols=ncols)

    elif None is not depth_images:
        n_images = len(depth_images)
        ncols, nrows, series = ncols, n_images // ncols, 1

        _, axs = plt.subplots(figsize=axes_size, nrows=nrows, ncols=ncols)

    elif None is not sharpness_images:
        n_images = len(sharpness_images)
        ncols, nrows, series = ncols, n_images // ncols, 1

        _, axs = plt.subplots(figsize=axes_size, nrows=nrows, ncols=ncols)

    else:
        raise ValueError('at least one of "depth_images" or "sharpness_images" must be specified')

    if nrows == 1:
        axs = [[axs]] if ncols == 1 else [axs]

    if None is not depth_images:
        depth_cmap = copy.copy(matplotlib.cm.get_cmap('viridis_r'))
        depth_cmap.set_bad(color='black')

        for row in range(nrows):
            for col in range(0, ncols, series):
                depth_idx = (row * ncols + col) // series
                depth_ax = axs[row][col]

                depth_image = depth_images[depth_idx].copy()
                background_idx = depth_image == 0
                depth_image[background_idx] = np.nan

                depth_ax.imshow(depth_image, interpolation='nearest', cmap=depth_cmap)
                depth_ax.axis('off')

    if None is not sharpness_images:
        sharpness_cmap = copy.copy(matplotlib.cm.get_cmap('coolwarm_r'))
        sharpness_cmap.set_bad(color='black')

        for row in range(nrows):
            for col in range(0, ncols, series):
                sharpness_idx = (row * ncols + col) // series
                sharpness_ax = axs[row][col + 1] if series == 2 else axs[row][col]

                sharpness_image = sharpness_images[sharpness_idx].copy()
                background_idx = sharpness_image == 0
                sharpness_image[background_idx] = np.nan

                tol = 1e-3
                sharpness_ax.imshow(sharpness_image, interpolation='nearest', cmap=sharpness_cmap,
                                    vmin=-tol, vmax=max_sharpness + tol)
                sharpness_ax.axis('off')

    plt.tight_layout(pad=0, h_pad=0.25, w_pad=0.25)
