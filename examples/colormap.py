import numpy as np
import vtk 
from vtk.util import numpy_support
import argparse 

from cs530.utils.vtk_rendering import make_actor, make_render_kit 
from cs530.utils.vtk_colors import make_colormap
from cs530.utils.vtk_colorbar import Colorbar

delta = 0.01

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Demonstrate the use of vtkColorTransferFunction')
    parser.add_argument('--gentle', action='store_true', help='Create a gentler transition to and from the neutral white')
    parser.add_argument('--highlight', type=float, nargs=3, help='Assign specific color to value zero, leaving the rest of the scale unchanged')
    parser.add_argument('--resolution', type=int, default=1024, help='Image resolution')
    args = parser.parse_args()

    t = np.linspace(0, 2 * np.pi, args.resolution)
    data2d = np.sin(t)[:, np.newaxis] * np.cos(t)[np.newaxis, :]

    image = vtk.vtkImageData(dimensions=(args.resolution, args.resolution, 1))
    image.GetPointData().SetScalars(numpy_support.numpy_to_vtk(data2d.flatten(order='F')))


    if not args.gentle:
        ctpt = [-1, -0.1, 0, 0.1, 1]
    else:
        ctpt = [-1, 1]
    cmap = make_colormap('seismic', ctpt)
    cbar = Colorbar(cmap)
    cbar.set_title('Waves', 20)

    actor = make_actor(image, cmap)
    actor2d = cbar.get()

    renderer, window, interactor = make_render_kit(actors=[actor, actor2d])
    interactor.Initialize()
    window.Render()
    interactor.Start()