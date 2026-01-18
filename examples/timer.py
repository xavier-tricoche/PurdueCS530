#!/usr/bin/env python

'''
 Purdue CS530 - Introduction to Scientific Visualization
 Spring 2026 
 
 Example showing how to use the TimerEvent to create a simple animation,
 and how to use vtkTextActor to display text in the visualization
'''

try:
    from PyQt6.QtWidgets import QApplication, QSlider, QPushButton, QTextEdit
    import PyQt6.QtCore as QtCore
    from PyQt6.QtCore import Qt, QTimer
except:
    try:
        from PySide6.QtWidgets import QApplication, QSlider, QPushButton, QTextEdit
        import PySide6.QtCore as QtCore
        from PySide6.QtCore import Qt, QTimer
    except:
        try:
            from PyQt5.QtWidgets import QApplication, QSlider, QPushButton, QTextEdit
            import PyQt5.QtCore as QtCore
            from PyQt5.QtCore import Qt, QTimer
        except ImportError:
            print("No PyQt/PySide available")
            sys.exit(1)

import vtk
import sys
import numpy as np
from vtk.util import numpy_support
import os

from utils.vtk_qt import QtVTKProgram, slider_setup
from utils.vtk_rendering import make_actor
from utils.vtk_helper import connect

frame_counter = 0

def make_sphere(resolution_theta, resolution_phi, edge_radius):
    # create and visualize sphere
    sphere_source = vtk.vtkSphereSource(radius=1, center=[0,0,0], resolution_theta=resolution_theta, resolution_phi=resolution_phi)

    # extract and visualize the edges
    edge_extractor = vtk.vtkExtractEdges()
    connect(sphere_source, edge_extractor)
    edge_tubes = vtk.vtkTubeFilter(radius=edge_radius)
    connect(edge_extractor, edge_tubes)
    return [sphere_source, edge_tubes]

def print_camera_settings(camera, text_window, log):
    # ---------------------------------------------------------------
    # Print out the current settings of the camera
    # ---------------------------------------------------------------
    text_window.setHtml("<div style='font-weight:bold'>Camera settings:</div><p><ul><li><div style='font-weight:bold'>Position:</div> {0}</li><li><div style='font-weight:bold'>Focal point:</div> {1}</li><li><div style='font-weight:bold'>Up vector:</div> {2}</li><li><div style='font-weight:bold'>Clipping range:</div> {3}</li></ul>".format(camera.GetPosition(), camera.GetFocalPoint(),camera.GetViewUp(),camera.GetClippingRange()))
    log.insertPlainText('Updated camera info\n');

class AnimationDemo (QtVTKProgram):

    def __init__(self, parent = None):
        super().__init__(parent)

        # Create GUI elements
        # Sliders
        self.slider_scale = QSlider()
        # Push buttons
        self.push_screenshot = QPushButton('Save screenshot')
        self.push_camera = QPushButton('Update camera info')
        self.push_quit = QPushButton('Quit')
        # Text windows
        self.camera_info = QTextEdit()
        self.camera_info.setReadOnly(True)
        self.camera_info.setAcceptRichText(True)
        self.camera_info.setHtml("<div style='font-weight: bold'>Camera settings</div>")
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.set_layout(buttons=[self.push_screenshot, self.push_camera, self.camera_info, self.log, self.push_quit], sliders=[("Scale", self.slider_scale)])

        print(self.layout)

        self.scale = 1
        self.dt = 0.1
        self.quiet = False
        self.timerid = -1

        # create dataset
        xs = np.linspace(-6*np.pi, 6*np.pi, 200)
        ys = np.linspace(-6*np.pi, 6*np.pi, 200)
        coords = np.meshgrid(xs, ys)
        x = coords[0]
        y = coords[1]
        sinc = np.sin(np.sqrt(x*x + y*y))
        vals = numpy_support.numpy_to_vtk(np.ravel(sinc))
        self.img = vtk.vtkImageData(dimensions=[200,200,1], spacing=[6*np.pi/100, 6*np.pi/100, 1])
        self.img.GetPointData().SetScalars(vals)

        self.warp = vtk.vtkWarpScalar(scale_factor=1)
        self.warp.SetInputData(self.img)
        actor = make_actor(self.warp, color=(1,1,0))

        self.text_actor = vtk.vtkTextActor(input="Scale factor: 1.0", position=(20, self.window.GetSize()[1] - 40))
        self.text_actor.GetTextProperty().SetFontSize(12)
        self.text_actor.GetTextProperty().SetColor(1.0, 1.0, 1.0)

        self.renderer.gradient_background = True 
        self.renderer.background = (0.75, 0.75, 0.75)
        self.renderer.AddActor(actor)
        self.renderer.AddActor2D(self.text_actor)
        self.window.SetSize(self.window.GetScreenSize())

        slider_setup(self.slider_scale, 10*self.scale, [-100, 100], 10)

    def scale_callback(self, val):
        self.scale = val/20
        self.warp.SetScaleFactor(self.scale)
        self.text_actor.SetInput(f"Scale factor: {self.scale:.1f}")
        self.text_actor.SetPosition(20, self.window.GetSize()[1] - 40)
        if not self.quiet:
            self.log.insertPlainText('Scale set to {}\n'.format(self.scale))
        self.draw()

    def save_frame_callback(self):
        fname = self.screenshot_callback()
        self.log.insertPlainText('Saved {}\n'.format(fname))

    def camera_callback(self):
        print_camera_settings(self.renderer.GetActiveCamera(), self.camera_info, self.log)

    def timer_callback(self):
        if self.scale == 5:
            self.dt = -0.1
        elif self.scale == -5:
            self.dt = 0.1
        self.scale += self.dt 
        self.quiet = True
        self.slider_scale.setValue(int(20*self.scale))
        self.quiet = False
        self.warp.SetScaleFactor(self.scale)
        self.window.Render()

if __name__=="__main__":
    global args
    import argparse

    parser = argparse.ArgumentParser(
        description='Illustrate the use of PyQt6 with VTK')
    parser.add_argument('-r', '--resolution', type=int, metavar='int', nargs=2, help='Image resolution', default=[1024, 768])
    parser.add_argument('-o', '--output', type=str, metavar='filename', help='Base name for screenshots', default='frame_')
    parser.add_argument('-v', '--verbose', action='store_true', help='Toggle on verbose output')

    args = parser.parse_args()

    app = QApplication(sys.argv)
    demo = AnimationDemo()
    demo.window.SetSize(args.resolution[0], args.resolution[1])
    demo.log.insertPlainText('Set render window resolution to {}\n'.format(args.resolution))
    demo.show()
    demo.setWindowState(Qt.WindowState.WindowMaximized)  # Maximize the window
    demo.interactor.EnableRenderOn()
    demo.interactor.Initialize() # Need this line to actually show
                             # the render inside Qt
    timer = QTimer()
    timer.timeout.connect(demo.timer_callback)
    demo.slider_scale.valueChanged.connect(demo.scale_callback)
    demo.push_screenshot.clicked.connect(demo.save_frame_callback)
    demo.push_camera.clicked.connect(demo.camera_callback)
    demo.push_quit.clicked.connect(demo.quit_callback)
    timer.start(20)
    sys.exit(app.exec())
