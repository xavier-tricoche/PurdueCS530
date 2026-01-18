#!/usr/bin/env python

'''
 Purdue CS530 - Introduction to Scientific Visualization
 Spring 2026 

 This program demonstrates how to use VTK with Qt to create a simple GUI 
 comprising slider bars, push buttons, text windows, and check boxes.
'''

import vtk
import argparse
import sys

try:
    from PyQt6.QtWidgets import QApplication, QLabel, QCheckBox, QGridLayout, QPushButton, QSlider, QTextEdit
    from PyQt6.QtCore import Qt
except ImportError:
    try:
        from PySide6.QtWidgets import QApplication, QLabel, QCheckBox, QGridLayout, QPushButton, QSlider, QTextEdit
        from PySide6.QtCore import Qt
    except ImportError:
        from PyQt5.QtWidgets import QApplication, QLabel, QCheckBox, QGridLayout, QPushButton, QSlider, QTextEdit
        from PyQt5.QtCore import Qt

from cs530.utils.vtk_rendering import take_screenshot, make_actor
from cs530.utils.vtk_helper import connect
from cs530.utils.vtk_qt import slider_setup, QtVTKProgram

frame_counter = 0

def make_sphere(resolution_theta, resolution_phi, edge_radius):
    # create and visualize sphere
    sphere_source = vtk.vtkSphereSource(radius=1.0, center=(0.0, 0.0, 0.0), theta_resolution=resolution_theta, phi_resolution=resolution_phi)

    # extract and visualize the edges
    edge_extractor = vtk.vtkExtractEdges()
    connect(sphere_source, edge_extractor)
    edge_tubes = vtk.vtkTubeFilter(radius=edge_radius, number_of_sides=10)
    connect(edge_extractor, edge_tubes)
    return [sphere_source, edge_tubes]

def save_frame(window, log):
    global frame_counter
    global args
    # ---------------------------------------------------------------
    # Save current contents of render window to PNG file
    # ---------------------------------------------------------------
    file_name = args.output + str(frame_counter).zfill(5) + ".png"
    take_screenshot(window, file_name)
    frame_counter += 1

def print_camera_settings(camera, text_window, log):
    # ---------------------------------------------------------------
    # Print out the current settings of the camera
    # ---------------------------------------------------------------
    text_window.setHtml("<div style='font-weight:bold'>Camera settings:</div><p><ul><li><div style='font-weight:bold'>Position:</div> {0}</li><li><div style='font-weight:bold'>Focal point:</div> {1}</li><li><div style='font-weight:bold'>Up vector:</div> {2}</li><li><div style='font-weight:bold'>Clipping range:</div> {3}</li></ul>".format(camera.GetPosition(), camera.GetFocalPoint(),camera.GetViewUp(),camera.GetClippingRange()))
    log.insertPlainText('Updated camera info\n');


class QtDemo (QtVTKProgram):

    def __init__(self, parent = None):
        super().__init__(parent)

        # Create GUI elements
        # Sliders
        self.slider_theta = QSlider()
        self.slider_phi = QSlider()
        self.slider_radius = QSlider()
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
        self.frame_basename = args.output

        self.checkbox = QCheckBox("Show edges")
        self.checkbox.setChecked(True)

        # Organize them on the grid layout 
        # syntax: addWidget(widget, row, column, row_span, column_span)
        grid_layout = QGridLayout(self.central_widget)
        grid_layout.addWidget(self.vtk_widget, 0, 0, 5, 4)
        grid_layout.addWidget(QLabel("Theta resolution"), 5, 0, 1, 1)
        grid_layout.addWidget(self.slider_theta, 5, 1, 1, 1)
        grid_layout.addWidget(QLabel("Phi resolution"), 6, 0, 1, 1)
        grid_layout.addWidget(self.slider_phi, 6, 1, 1, 1)
        grid_layout.addWidget(QLabel("Edge radius"), 5, 2, 1, 1)
        grid_layout.addWidget(self.slider_radius, 5, 3, 1, 1)
        grid_layout.addWidget(self.push_screenshot, 0, 5, 1, 1)
        grid_layout.addWidget(self.push_camera, 1, 5, 1, 1)
        grid_layout.addWidget(self.checkbox, 2, 5, 1, 1)
        grid_layout.addWidget(self.camera_info, 3, 4, 1, 2)
        grid_layout.addWidget(self.log, 4, 4, 1, 2)
        grid_layout.addWidget(self.push_quit, 5, 5, 1, 1)
        # assign that layout to our window 
        self.set_layout(layout=grid_layout)

        self.theta = 20
        self.phi = 20
        self.radius = 0.001

        # Source
        [self.sphere, self.edges] = make_sphere(self.theta, self.phi, self.radius)
        sphere_actor = make_actor(self.sphere, color=(1, 1, 0))
        self.edge_actor = make_actor(self.edges, color=(0, 0, 1))

        # Add actors to the renderer
        self.renderer.AddActor(sphere_actor)
        self.renderer.AddActor(self.edge_actor)
        self.renderer.GradientBackgroundOn()  # Set gradient for background
        self.renderer.SetBackground(0.75, 0.75, 0.75)  # Set background to silver

        slider_setup(self.slider_theta, self.theta, [3, 200], 10)
        slider_setup(self.slider_phi, self.phi, [3, 200], 10)
        slider_setup(self.slider_radius, self.radius*100, [1, 10], 1)

    def theta_callback(self, val):
        self.theta = val
        self.sphere.theta_resolution = self.theta
        self.log.insertPlainText('Theta resolution set to {}\n'.format(self.theta))
        self.draw()

    def phi_callback(self, val):
        self.phi = val
        self.sphere.phi_resolution = self.phi
        self.log.insertPlainText('Phi resolution set to {}\n'.format(self.phi))
        self.draw()

    def radius_callback(self, val):
        self.radius = val/1000.
        self.edges.radius = self.radius
        self.log.insertPlainText('Edge radius set to {}\n'.format(self.radius))
        self.draw()

    def checkbox_callback(self, checked):
        if checked:
            self.edge_actor.VisibilityOn()
        else:
            self.edge_actor.VisibilityOff()
        self.draw()

    def logged_screenshot_callback(self):
        fname = self.screenshot_callback()
        if args.verbose:
            print(fname + " has been successfully exported")
        self.log.insertPlainText('Exported {}\n'.format(fname))

    def camera_callback(self):
        print_camera_settings(self.renderer.GetActiveCamera(), self.camera_info, self.log)

    def quit_callback(self):
        sys.exit()

if __name__=="__main__":
    global args

    parser = argparse.ArgumentParser(
        description='Illustrate the use of PyQt5 with VTK')
    parser.add_argument('-r', '--resolution', type=int, metavar='int', nargs=2, help='Image resolution', default=[1024, 768])
    parser.add_argument('-o', '--output', type=str, metavar='filename', help='Base name for screenshots', default='frame_')
    parser.add_argument('-v', '--verbose', action='store_true', help='Toggle on verbose output')

    args = parser.parse_args()

    app = QApplication(sys.argv)
    demo = QtDemo()
    demo.size = args.resolution
    demo.log.insertPlainText('Set render window resolution to {}\n'.format(args.resolution))
    demo.show()
    demo.setWindowState(Qt.WindowState.WindowMaximized)  # Maximize the window
    demo.interactor.Initialize() # Need this line to actually show
                             # the render inside Qt

    demo.slider_theta.valueChanged.connect(demo.theta_callback)
    demo.slider_phi.valueChanged.connect(demo.phi_callback)
    demo.slider_radius.valueChanged.connect(demo.radius_callback)
    demo.push_screenshot.clicked.connect(demo.logged_screenshot_callback)
    demo.push_camera.clicked.connect(demo.camera_callback)
    demo.push_quit.clicked.connect(demo.quit_callback)
    demo.checkbox.stateChanged.connect(demo.checkbox_callback)
    sys.exit(app.exec())
