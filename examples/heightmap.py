'''
Purdue CS530 - Introduction to Scientific Visualization
Spring 2026

Example showing how vtkWarpScalar can be used to create a heightfield
from a scalar image.
'''

import numpy as np 
import vtk 
from vtk.util import numpy_support as nps
import math
import argparse

from cs530.utils.vtk_io import read_vtk_file
from cs530.utils.vtk_rendering import make_actor, make_render_kit

# create a sinc raster image
# Note: sinc function is sin(x)/x and is a perfect reconstruction filter
def make_sinc(n, width):
    dh = 2*width/float(n)
    data = np.zeros((n*n))
    for j in range(n):
        y = -width + j*dh
        for i in range(n):
            x = -width + i*dh
            r = math.sqrt(x*x + y*y)
            if r == 0:
                data[i+j*n] = 1
            else:
                data[i+j*n] = math.sin(r)/r

    # pack the data into a VTK data structure
    vtk_array = nps.numpy_to_vtk(data)
    image = vtk.vtkImageData(dimensions=[n, n, 1], spacing=[dh, dh, 1], origin=[-width, width, 0])
    image.GetPointData().SetScalars(vtk_array)
    return image

# create a height field from it
def do_warp(input, factor): 
    warp = vtk.vtkWarpScalar(scale_factor=factor)
    warp.SetInputData(input)
    return warp
   
def on_sphere(image, radius=1, center=[0, 0, 0]):
    w, h, _ = image.GetDimensions()
    sphere_src = vtk.vtkSphereSource(center=center, radius=radius, theta_resolution=h, phi_resolution=w)
    sphere_src.Update()
    sphere = sphere_src.GetOutput()
    values = nps.vtk_to_numpy(image.GetPointData().GetScalars())
    new_values = np.zeros((2+w*(h-2)))
    new_values[0] = values[0]
    new_values[1] = values[-1]
    new_values[2:] = values[w:(h-1)*w]
    sphere.GetPointData().SetScalars(nps.numpy_to_vtk(new_values))
    return sphere

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Uses vtkWarpScalar')
    parser.add_argument('-i', '--input', type=str, help='Input image dataset')
    parser.add_argument('-n', '--number', type=int, default=101, help='Number of points along X and Y')
    parser.add_argument('-w', '--width', type=float, default=20., help='Half-width of considered domain')
    parser.add_argument('-f', '--factor', type=float, default=20., help='Warp scale factor')
    parser.add_argument('-r', '--resolution', type=int, nargs=2, default=[1024, 1024], help='Image resolution')
    parser.add_argument('--on_sphere', action='store_true', help='Map sinc on a sphere')
    args = parser.parse_args()

    if args.input is None:
        image = make_sinc(args.number, args.width)
    else:
        image = read_vtk_file(args.input)

    if args.on_sphere:
        sphere = on_sphere(image)
        warp = do_warp(sphere, args.factor)
    else:
        warp = do_warp(image, args.factor)
    
    actor = make_actor(warp)
    renderer, window, interactor = make_render_kit(actors=[actor], size=args.resolution)

    interactor.Initialize()
    window.Render()
    interactor.Start()