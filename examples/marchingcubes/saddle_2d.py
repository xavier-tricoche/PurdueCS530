#!/usr/bin/env python
"""
Simple program illustrating the role of the saddle point
in resolving the ambiguity in marching squares for bilinear
cells.
"""

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QSlider, QGridLayout, QLabel
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import pyqtSignal, Qt
# from PyQt5 import Qt, QtCore, QtGui
import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import sys
import numpy as np
from vtk.util import numpy_support

def connect(data, dest):
    dest.SetInputData(data)

def plug(outlet, inlet):
    inlet.SetInputConnection(outlet.GetOutputPort())

def bilinear(x, y, coef):
    f00 = coef["f00"]
    f10 = coef["f10"]
    f11 = coef["f11"]
    f01 = coef["f01"]
    f = f00*(1-x)*(1-y) + f10*x*(1-y) + f01*(1-x)*y + f11*x*y
    return f

def saddle(coef):
    f00 = coef["f00"]
    f10 = coef["f10"]
    f11 = coef["f11"]
    f01 = coef["f01"]
    #dfdx = (f10-f00)*(1-y) + (f11-f01)*y = y*(f11-f01-f10+f00) + (f10-f00)
    #dfdy = (f01-f00)*(1-x) + (f11-f10)*x = x*(f11-f10-f01+f00) + (f01-f00)
    denom = f11-f10-f01+f00
    if denom == 0: return [-1, -1, 0]
    else: return [ (f00-f01)/denom, (f00-f10)/denom ]

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName('The Main Window')
        MainWindow.setWindowTitle('Illustration of Saddle Method')
        self.centralWidget = QWidget(MainWindow)
        self.gridlayout = QGridLayout(self.centralWidget)
        self.vtkWidget = QVTKRenderWindowInteractor(self.centralWidget)
        self.gridlayout.addWidget(self.vtkWidget, 0, 0, 1, 5)
        # Instantiate the sliders
        self.sliderf00 = QSlider()
        self.sliderf11 = QSlider()
        self.sliderf01 = QSlider()
        self.sliderf10 = QSlider()
        self.gridlayout.addWidget(QLabel("f00"), 1, 0)
        self.gridlayout.addWidget(self.sliderf00, 1, 1)
        self.gridlayout.addWidget(QLabel("f01"), 1, 3)
        self.gridlayout.addWidget(self.sliderf01, 1, 4)
        self.gridlayout.addWidget(QLabel("f10"), 2, 0)
        self.gridlayout.addWidget(self.sliderf10, 2, 1)
        self.gridlayout.addWidget(QLabel("f11"), 2, 3)
        self.gridlayout.addWidget(self.sliderf11, 2, 4)
        MainWindow.setCentralWidget(self.centralWidget)

class SaddleMethodDemo(QMainWindow):

    def __init__(self, parent = None):
        QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Source
        n = 100
        dx = 1.0/(n-1)
        self.grid = vtk.vtkImageData()
        self.grid.SetOrigin(0, 0, 0)
        self.grid.SetSpacing(dx, dx, dx)
        self.grid.SetDimensions(n, n, 1)
        self.X, self.Y = np.mgrid[0:1:complex(0,n), 0:1:complex(0,n)]
        self.X = self.X.flatten('F')
        self.Y = self.Y.flatten('F')

        self.coef = { "f00" : 0, \
                      "f10" : 0, \
                      "f01" : 0, \
                      "f11" : 0  }
        cell_mapper = vtk.vtkDataSetMapper()
        connect(self.grid, cell_mapper)
        cell_mapper.ScalarVisibilityOff()

        cell_actor = vtk.vtkActor()
        cell_actor.SetMapper(cell_mapper)
        cell_actor.GetProperty().SetColor(0.04, 0.05, 0.35)
        cell_actor.GetProperty().SetOpacity(0.2)

        self.sphere = vtk.vtkSphereSource()
        self.sphere.SetRadius(0.02)
        self.sphere.SetCenter(0.5, 0.5, 0) # dummy coordinates
        self.sphere.SetThetaResolution(24)
        self.sphere.SetPhiResolution(24)

        sphere_mapper = vtk.vtkPolyDataMapper()
        plug(self.sphere, sphere_mapper)
        sphere_mapper.ScalarVisibilityOff()

        self.sphere_actor = vtk.vtkActor()
        self.sphere_actor.SetMapper(sphere_mapper)
        self.sphere_actor.GetProperty().SetColor(1, 0, 0)
        self.sphere_actor.SetVisibility(False)

        self.make_data()

        # Isolines
        iso = vtk.vtkContourFilter()
        iso.SetValue(0, 0)
        connect(self.grid, iso)

        tubes = vtk.vtkTubeFilter()
        plug(iso, tubes)
        tubes.SetRadius(0.005)
        tubes.SetNumberOfSides(12)

        tube_mapper = vtk.vtkPolyDataMapper()
        plug(tubes, tube_mapper)
        tube_mapper.ScalarVisibilityOff()
        tube_actor = vtk.vtkActor()
        tube_actor.SetMapper(tube_mapper)
        tube_actor.GetProperty().SetColor(1, 1, 0)

        # warped surface
        self.scale = 1
        warp = vtk.vtkWarpScalar()
        connect(self.grid, warp)
        warp.SetScaleFactor(self.scale)

        surf_mapper = vtk.vtkDataSetMapper()
        plug(warp, surf_mapper)
        surf_mapper.ScalarVisibilityOff()

        surf_actor = vtk.vtkActor()
        surf_actor.GetProperty().SetColor(0.6, 0., 0.)
        surf_actor.SetMapper(surf_mapper)

        # cell frame
        frame = vtk.vtkPlaneSource()
        frame.SetOrigin(0, 0, 0)
        frame.SetPoint1(1, 0, 0)
        frame.SetPoint2(0, 1, 0)
        frame_edges = vtk.vtkExtractEdges()
        plug(frame, frame_edges)
        frame_tubes = vtk.vtkTubeFilter()
        plug(frame_edges, frame_tubes)
        frame_tubes.SetRadius(0.005)
        frame_tubes.SetNumberOfSides(12)
        frame_tubes.SetCapping(True)
        frame_mapper = vtk.vtkPolyDataMapper()
        plug(frame_tubes, frame_mapper)
        frame_mapper.ScalarVisibilityOff()
        frame_actor = vtk.vtkActor()
        frame_actor.SetMapper(frame_mapper)
        frame_actor.GetProperty().SetColor(0, 0, 1)

        # Create the Renderer
        self.ren = vtk.vtkRenderer()
        self.ren.AddActor(cell_actor)
        self.ren.AddActor(surf_actor)
        self.ren.AddActor(tube_actor)
        self.ren.AddActor(frame_actor)
        self.ren.AddActor(self.sphere_actor)
        self.ren.GradientBackgroundOn()  # Set gradient for background
        self.ren.SetBackground(0.75, 0.75, 0.75)  # Set background to silver
        self.ui.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = self.ui.vtkWidget.GetRenderWindow().GetInteractor()

        # Setting up widgets
        def slider_setup(slider, val, bounds, interv):
            slider.setOrientation(QtCore.Qt.Horizontal)
            slider.setValue(int(val))
            slider.setTracking(False)
            slider.setTickInterval(interv)
            slider.setTickPosition(QSlider.TicksAbove)
            slider.setRange(bounds[0], bounds[1])

        slider_setup(self.ui.sliderf00, 0, [-100, 100], 10)
        slider_setup(self.ui.sliderf10, 0, [-100, 100], 10)
        slider_setup(self.ui.sliderf11, 0, [-100, 100], 10)
        slider_setup(self.ui.sliderf01, 0, [-100, 100], 10)

    def f00_callback(self, val):
        val = val/100.
        self.coef["f00"] = val
        self.make_data()

    def f01_callback(self, val):
        val = val/100.
        self.coef["f01"] = val
        self.make_data()

    def f11_callback(self, val):
        val = val/100.
        self.coef["f11"] = val
        self.make_data()

    def f10_callback(self, val):
        val = val/100.
        self.coef["f10"] = val
        self.make_data()

    def make_data(self):
        values = bilinear(self.X, self.Y, self.coef)
        saddle_pos = saddle(self.coef)
        if saddle_pos[0] >= 0 and saddle_pos[0] <= 1 \
            and saddle_pos[1] >= 0 and saddle_pos[1] <= 1:
            [ x, y ] = saddle_pos
            z = bilinear(x, y, self.coef)
            self.sphere.SetCenter(saddle_pos[0], saddle_pos[1], \
                self.scale*bilinear(saddle_pos[0], saddle_pos[1], self.coef))
            self.sphere_actor.SetVisibility(True)
            if z > 0: self.sphere_actor.GetProperty().SetColor(1, 0, 0)
            elif z < 0: self.sphere_actor.GetProperty().SetColor(0, 0, 1)
            else: self.sphere_actor.GetProperty().SetColor(1, 1, 1)
        else:
            self.sphere_actor.SetVisibility(False)

        self.array = numpy_support.numpy_to_vtk(values)
        self.grid.GetPointData().SetScalars(self.array)
        self.ui.vtkWidget.GetRenderWindow().Render()


if __name__ == "__main__":

    app = QApplication(sys.argv)
    window = SaddleMethodDemo()
    window.show()
    window.setWindowState(Qt.WindowMaximized)  # Maximize the window
    window.iren.Initialize() # Need this line to actually show
                             # the render inside Qt

    window.ui.sliderf00.valueChanged.connect(window.f00_callback)
    window.ui.sliderf10.valueChanged.connect(window.f10_callback)
    window.ui.sliderf11.valueChanged.connect(window.f11_callback)
    window.ui.sliderf01.valueChanged.connect(window.f01_callback)
    sys.exit(app.exec_())
