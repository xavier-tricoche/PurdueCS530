#!/usr/bin/env python

'''
 Purdue CS530 - Introduction to Scientific Visualization
 Spring 2026

 Simple example showing how to create a vtkAlgorithm (aka filter) and how
 to interact with it in a VTK pipeline using a QtVTKProgram parent class.
 '''

import vtk
import argparse
import sys

try:
    from PyQt6.QtWidgets import QApplication, QColorDialog, QPushButton, QSlider, QTextEdit
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor
except ImportError:
    try:
        from PySide6.QtWidgets import QApplication, QColorDialog, QPushButton, QSlider, QTextEdit
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor
    except ImportError:
        from PyQt5.QtWidgets import QApplication, QColorDialog, QPushButton, QSlider, QTextEdit
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QColor

from utils import vtk_rendering_helper as vrh
from utils import vtk_helper as vh
from utils import vtk_qt as vqt
from utils import vtk_colorbar as vcb
from utils import vtk_camera as vcam

frame_counter = 0

from vtk.util.vtkAlgorithm import VTKPythonAlgorithmBase
import vtk.util.numpy_support

frame_counter = 0

def print_camera_settings(camera, text_window, log):
    # ---------------------------------------------------------------
    # Print out the current settings of the camera
    # ---------------------------------------------------------------
    text_window.setHtml("<div style='font-weight:bold'>Camera settings:</div><p><ul><li><div style='font-weight:bold'>Position:</div> {0}</li><li><div style='font-weight:bold'>Focal point:</div> {1}</li><li><div style='font-weight:bold'>Up vector:</div> {2}</li><li><div style='font-weight:bold'>Clipping range:</div> {3}</li></ul>".format(camera.GetPosition(), camera.GetFocalPoint(),camera.GetViewUp(),camera.GetClippingRange()))
    log.insertPlainText('Updated camera info\n');

# The following class creates an algorithm that produces a sphere 
# (like vtkSphereSource) along with the latitude coordinates assigned
# at each vertex. 
class MySphere(VTKPythonAlgorithmBase):
    def __init__(self):
        VTKPythonAlgorithmBase.__init__(self,
              nInputPorts=0, # it's a source: no input
              nOutputPorts=1, outputType='vtkPolyData')
        # initial sphere parameterization
        self.theta = 10
        self.phi = 10
        self.center = [ 0, 0, 0]
        self.radius = 1
        self.modified = True

    def ComputeLatitude(self):
        coords = vtk.util.numpy_support.vtk_to_numpy(self.sphere.GetPoints().GetData())
        values = coords[:,2]*90
        data = vtk.util.numpy_support.numpy_to_vtk(values)
        data.SetName('latitude')
        self.sphere.GetPointData().AddArray(data)
        self.sphere.GetPointData().SetActiveScalars('latitude')

    # This is the function that does the work of keeping the sphere up to date
    def Update(self):
        sphere_src = vtk.vtkSphereSource(center=self.center, radius=self.radius, theta_resolution=self.theta, phi_resolution=self.phi)
        sphere_src.Update()
        self.sphere = sphere_src.GetOutput()
        self.ComputeLatitude()

    # Reimplemented from vtkSphereSource
    def SetThetaResolution(self, theta):
        self.theta = theta
        self.Modified()

    # Reimplemented from vtkSphereSource
    def SetPhiResolution(self, phi):
        self.phi = phi
        self.Modified()

    # Reimplemented from vtkSphereSource
    def SetCenter(self, center):
        self.center = center
        self.Modified()

    # Reimplemented from vtkSphereSource
    def SetRadius(self, radius):
        self.radius = radius
        self.Modified()

    # This function will be called after each modification
    # each time the rendering pipeline is re-executed.
    def RequestData(self, request, inInfo, outInfo):
        output = vtk.vtkPolyData.GetData(outInfo)
        self.Update()
        output.ShallowCopy(self.sphere)
        return 1

class AlgoDemo (vqt.QtVTKProgram):
    def __init__(self, parent = None):
        super().__init__(parent)

        # creeate a color map to represent latitude information
        self.ctf = vtk.vtkColorTransferFunction()
        self.ctf.AddRGBPoint(-90, 0, 0, 1) # south pole is blue
        self.ctf.AddRGBPoint(0, 0.5, 0.5, 0.5) # equator is gray
        self.ctf.AddRGBPoint(90, 1, 1, 0) # north pole is yellow

        # create a color bar to explain what those colors mean
        bar = vcb.colorbar(self.ctf)
        bar.set_label(nlabels=7, size=10)
        bar.set_position([0.9, 0.5]) # right center of the window
        bar.set_size(width=80, height=300)
        bar.set_title(title="Latitude", size=10)
        # The color bar is drawn directly on the screen, it does 
        # not belong to the 3D scene
        self.renderer.AddActor2D(bar.get())
        # Create GUI elements
        # Sliders
        self.slider_theta = QSlider()
        self.slider_phi = QSlider()
        self.slider_radius = QSlider()
        # Push buttons
        self.push_screenshot = QPushButton('Save screenshot')
        self.push_camera = QPushButton('Update camera info')
        self.push_color = QPushButton('Change edge color')
        self.push_quit = QPushButton('Quit')
        # Text windows
        self.camera_info = QTextEdit()
        self.camera_info.setReadOnly(True)
        self.camera_info.setAcceptRichText(True)
        self.camera_info.setHtml("<div style='font-weight: bold'>Camera settings</div>")
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.set_layout(buttons=[self.push_screenshot, self.push_camera, self.push_color, self.camera_info, self.log, self.push_quit], 
                        sliders=[['Theta resolution', self.slider_theta], 
                                 ['Phi resolution', self.slider_phi], 
                                 ['Edge radius', self.slider_radius]])

        self.theta = 20
        self.phi = 20
        self.radius = 1

        # Source
        self.sphere = MySphere()
        self.sphere.SetThetaResolution(self.theta)
        self.sphere.SetPhiResolution(self.phi)
        self.sphere.SetRadius(self.radius)
        sphere_actor = vrh.make_actor(self.sphere, ctf=self.ctf)
        self.edges = vtk.vtkExtractEdges()
        vh.connect(self.sphere, self.edges)
        self.edge_tubes = vtk.vtkTubeFilter(number_of_sides=10, capping=True, radius=self.radius/1000.0)
        vh.connect(self.edges, self.edge_tubes)
        self.edge_actor = vrh.make_actor(self.edge_tubes, color=(0, 0, 1))
        self.color = (0, 0, 1)

        # Create the Renderer
        self.renderer.AddActor(sphere_actor)
        self.renderer.AddActor(self.edge_actor)
        self.renderer.GradientBackgroundOn()  # Set gradient for background
        self.renderer.SetBackground(0.75, 0.75, 0.75)  # Set background to silver

        vqt.slider_setup(self.slider_theta, self.theta, [3, 200], 10)
        vqt.slider_setup(self.slider_phi, self.phi, [3, 200], 10)
        vqt.slider_setup(self.slider_radius, 1, [1, 10], 1)

    def theta_callback(self, val):
        self.theta = val
        self.sphere.SetThetaResolution(self.theta)
        self.log.insertPlainText('Theta resolution set to {}\n'.format(self.theta))
        self.draw()

    def phi_callback(self, val):
        self.phi = val
        self.sphere.SetPhiResolution(self.phi)
        self.log.insertPlainText('Phi resolution set to {}\n'.format(self.phi))
        self.draw()

    def radius_callback(self, val):
        self.edge_tubes.SetRadius(self.radius*float(val)/1000.0)
        self.log.insertPlainText('Edge radius set to {}\n'.format(self.radius*float(val)/1000.0))
        self.draw()

    def logged_screenshot_callback(self):
        fname = self.screenshot_callback()
        self.log.insertPlainText('Saved {}\n'.format(fname))

    def camera_callback(self):
        print_camera_settings(self.renderer.GetActiveCamera(), self.camera_info, self.log)

    def color_callback(self):
        dialog = QColorDialog()
        dialog.setCurrentColor(QColor(int(self.color[0]*255), int(self.color[1]*255), int(self.color[2]*255)))
        color = dialog.getColor()
        self.color = [color.redF(), color.greenF(), color.blueF()]
        self.edge_actor.GetProperty().SetColor(self.color[0], self.color[1], self.color[2])
        self.log.insertPlainText('Edge color set to {}\n'.format([self.color[0], self.color[1], self.color[2]]))
        self.draw()

    def quit_callback(self):
        sys.exit()

if __name__=="__main__":
    global args

    parser = argparse.ArgumentParser(
        description='Illustrate the use of PyQt5 with VTK')
    parser.add_argument('-r', '--resolution', type=int, metavar='int', nargs=2, help='Image resolution', default=[1024, 768])
    parser.add_argument('-o', '--output', type=str, metavar='filename', help='Base name for screenshots', default='frame_')
    parser.add_argument('-v', '--verbose', action='store_true', help='Toggle on verbose output')
    parser.add_argument('-c', '--camera', type=str, help='Import camera settings')

    args = parser.parse_args()

    app = QApplication(sys.argv)
    demo = AlgoDemo()
    demo.window.SetSize(args.resolution[0], args.resolution[1])
    demo.log.insertPlainText('Set render window resolution to {}\n'.format(args.resolution))
    demo.show()
    demo.setWindowState(Qt.WindowState.WindowMaximized)  # Maximize the window
    demo.interactor.Initialize() # Need this line to actually show
                             # the render inside Qt

    demo.slider_theta.valueChanged.connect(demo.theta_callback)
    demo.slider_phi.valueChanged.connect(demo.phi_callback)
    demo.slider_radius.valueChanged.connect(demo.radius_callback)
    demo.push_screenshot.clicked.connect(demo.logged_screenshot_callback)
    demo.push_color.clicked.connect(demo.color_callback)
    demo.push_camera.clicked.connect(demo.camera_callback)
    demo.push_quit.clicked.connect(demo.quit_callback)
    sys.exit(app.exec())
