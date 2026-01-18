import numpy as np
import vtk 
from vtk.util import numpy_support
import argparse 

from utils.vtk_rendering import make_actor, make_render_kit 

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

    cmap = vtk.vtkColorTransferFunction()
    cmap.AddRGBPoint(-1, 0, 0, 1)
    if args.gentle:
        cmap.AddRGBPoint(-0.1, 0.5, 0.5, 1) 
    if args.highlight is None:
        cmap.AddRGBPoint(0, 1, 1, 1)
    else:
        cmap.AddRGBPoint(-delta, 1, 1, 1)
        cmap.AddRGBPoint(-delta+0.00001, args.highlight[0], args.highlight[1], args.highlight[2])
        cmap.AddRGBPoint(+delta-0.00001, args.highlight[0], args.highlight[1], args.highlight[2])
        cmap.AddRGBPoint(+delta, 1, 1, 1)
    if args.gentle:
        cmap.AddRGBPoint(0.1, 1, 1, 0.5)
    cmap.AddRGBPoint(1, 1, 1, 0)

    actor = make_actor(image, cmap)
    renderer, window, interactor = make_render_kit(actors=[actor])
    interactor.Initialize()
    window.Render()
    interactor.Start()