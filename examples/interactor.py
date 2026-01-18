#!/usr/bin/env python

'''
Purdue CS530 - Introduction to Scientific Visualization
Spring 2026

Simple example to show how vtkRenderWindowInteractor can be customized
to support additional user requests. Here, a sphere is being rendered
and three key-press actions are defined: 's' saves the current frame to
a PNG file, 'c' prints out the current camera setting, and 'q' exits
the application.
'''
import sys
import vtk
import argparse

from utils.vtk_helper import connect
from utils.vtk_rendering import make_actor, make_render_kit, take_screenshot
from utils.vtk_camera import print_camera
frame_counter = 0

def make_sphere(renderer):
    # ---------------------------------------------------------------
    # The following code is identical to render_demo.py...
    # ---------------------------------------------------------------
    # create a sphere
    sphere_src = vtk.vtkSphereSource(radius=1.0, center=(0.0, 0.0, 0.0), theta_resolution=20, phi_resolution=20)
    sphere_actor = make_actor(sphere_src, color=(1, 0.5, 0))
    # extract the edges
    edge_extractor = vtk.vtkExtractEdges()
    connect(sphere_src, edge_extractor) 
    edge_actor = make_actor(edge_extractor, color=(0, 0.5, 0), line_width=3)
    # add resulting primitives to renderer
    renderer.AddActor(sphere_actor)
    renderer.AddActor(edge_actor)

class Callback:
    def __init__(self, renderer, window, args):
        self.renderer = renderer
        self.window = window
        self.args = args
        self.frame_counter = 0

    def save_frame(self):
        # ---------------------------------------------------------------
        # Save current contents of render window to PNG file
        # ---------------------------------------------------------------
        file_name = self.args.output + str(self.frame_counter).zfill(5) + ".png"
        take_screenshot(self.window, file_name)
        self.frame_counter += 1
        if self.args.verbose:
            print(file_name + " has been successfully exported")

    def __call__(self, obj, event):
        # ---------------------------------------------------------------
        # Attach actions to specific keys
        # ---------------------------------------------------------------
        key = obj.key_sym
        if key == "h":
            print("Commands:\n 's': save frame\n 'c': print camera setting\n 'h': print this message\n 'q': quit the program")
        elif key == "s":
            self.save_frame()
        elif key == "c":
            print_camera(self.renderer.GetActiveCamera())
        elif key == "q":
            if self.args.verbose:
                print("User requested exit.")
            sys.exit()

def main():

    parser = argparse.ArgumentParser(
        description='Illustrate the use of vtkRenderWindowInteractor')
    parser.add_argument('-r', '--resolution', type=int, metavar='int', nargs=2, help='Image resolution', default=[1024, 768])
    parser.add_argument('-b', '--background', type=int, metavar='int', nargs=3, help='Background color', default=[0,0,0])
    parser.add_argument('-o', '--output', type=str, metavar='filename', help='Base name for screenshots', default='frame_')
    parser.add_argument('-v', '--verbose', action='store_true', help='Toggle on verbose output')

    args = parser.parse_args()
    renderer, window, interactor = make_render_kit(size=args.resolution, bg=args.background)

    callback = Callback(renderer, window, args)

    make_sphere(renderer)
    renderer.ResetCamera()

    # ---------------------------------------------------------------
    # Add a custom callback function to the interactor
    # ---------------------------------------------------------------
    interactor.AddObserver("KeyPressEvent", callback)

    interactor.Initialize()
    window.Render()
    interactor.Start()

if __name__=="__main__":
      main()
