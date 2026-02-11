#!/usr/bin/env python
"""
Simple program illustrating the role of the saddle point
in resolving the ambiguity in marching cubes for trilinear
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

n=50

def connect(data, dest):
    dest.SetInputData(data)

def plug(outlet, inlet):
    inlet.SetInputConnection(outlet.GetOutputPort())

def trilinear(x, y, z, coef):
    fneg = coef["fneg"]
    fpos = coef["fpos"]
    return fneg*(1 - x - y - z + x*y + y*z + x*z) + \
        fpos*(x + y + z - x*y - x*z - y*z)

def saddle(coef):
    return [0.5, 0.5, 0.5]

def make_sphere():
    sphere = vtk.vtkSphereSource()
    sphere.SetRadius(0.02)
    sphere.SetThetaResolution(24)
    sphere.SetPhiResolution(24)
    return sphere

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName('The Main Window')
        MainWindow.setWindowTitle('Illustration of Saddle Method')
        self.centralWidget = QWidget(MainWindow)
        self.gridlayout = QGridLayout(self.centralWidget)
        self.vtkWidget = QVTKRenderWindowInteractor(self.centralWidget)
        self.gridlayout.addWidget(self.vtkWidget, 0, 0, 1, 5)
        # Instantiate the sliders
        self.sliderfpos = QSlider()
        self.sliderfneg = QSlider()
        self.gridlayout.addWidget(QLabel("fpos"), 1, 0)
        self.gridlayout.addWidget(self.sliderfpos, 1, 1)
        self.gridlayout.addWidget(QLabel("fneg"), 1, 3)
        self.gridlayout.addWidget(self.sliderfneg, 1, 4)
        MainWindow.setCentralWidget(self.centralWidget)

class SaddleMethod3dDemo(QMainWindow):

    def __init__(self, parent = None):
        QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Source
        dx = 1.0/(n-1)
        self.grid = vtk.vtkImageData()
        self.grid.SetOrigin(0, 0, 0)
        self.grid.SetSpacing(dx, dx, dx)
        self.grid.SetDimensions(n, n, n)
        self.X, self.Y, self.Z = np.mgrid[0:1:complex(0,n), 0:1:complex(0,n), 0:1:complex(n)]
        self.X = self.X.flatten('F')
        self.Y = self.Y.flatten('F')
        self.Z = self.Z.flatten('F')

        self.coef = { "fpos" : 0, "fneg" : 0 }

        self.sphere = make_sphere()
        self.sphere.SetCenter(0.5, 0.5, 0.5)

        sphere_mapper = vtk.vtkPolyDataMapper()
        plug(self.sphere, sphere_mapper)
        sphere_mapper.ScalarVisibilityOff()

        self.sphere_actor = vtk.vtkActor()
        self.sphere_actor.SetMapper(sphere_mapper)
        self.sphere_actor.GetProperty().SetColor(0.5, 0.5, 0.5)
        self.sphere_actor.SetVisibility(True)

        self.make_data()

        # Isosurface
        iso = vtk.vtkContourFilter()
        iso.SetValue(0, 0)
        connect(self.grid, iso)

        iso_mapper = vtk.vtkPolyDataMapper()
        plug(iso, iso_mapper)
        iso_mapper.ScalarVisibilityOff()
        iso_actor = vtk.vtkActor()
        iso_actor.SetMapper(iso_mapper)
        iso_actor.GetProperty().SetColor(0.6, 0, 0)

        # cell frame
        frame = vtk.vtkCubeSource()
        frame.SetBounds(0, 1, 0, 1, 0, 1)

        p = []
        p.append([0, 0, 0])
        p.append([1, 0, 0])
        p.append([1, 1, 0])
        p.append([0, 1, 0])
        p.append([0, 0, 1])
        p.append([1, 0, 1])
        p.append([1, 1, 1])
        p.append([0, 1, 1])

        points = vtk.vtkPoints()
        for i in range(8):
            points.InsertNextPoint(p[i])

        l = []
        l.append([0, 1])
        l.append([1, 2])
        l.append([2, 3])
        l.append([3, 0])
        l.append([4, 5])
        l.append([5, 6])
        l.append([6, 7])
        l.append([7, 4])
        l.append([0, 4])
        l.append([1, 5])
        l.append([2, 6])
        l.append([3, 7])

        lines = vtk.vtkCellArray()
        for i in range(12):
            line = vtk.vtkLine()
            line.GetPointIds().SetId(0, l[i][0])
            line.GetPointIds().SetId(1, l[i][1])
            lines.InsertNextCell(line)

        polydata = vtk.vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetLines(lines)

        frame_mapper = vtk.vtkPolyDataMapper()
        frame_mapper.SetInputData(polydata)
        frame_actor = vtk.vtkActor()
        frame_actor.SetMapper(frame_mapper)
        frame_actor.GetProperty().SetColor(1,0,1)

        frame_mapper2 = vtk.vtkPolyDataMapper()
        frame_mapper2.SetInputConnection(frame.GetOutputPort())
        frame_actor2 = vtk.vtkActor()
        frame_actor2.SetMapper(frame_mapper2)
        frame_actor2.GetProperty().SetOpacity(0.2)
        frame_actor2.GetProperty().SetColor(1, 1, 1)

        self.ren = vtk.vtkRenderer()
        for i in range(8):
            sphere = make_sphere()
            sphere.SetCenter(p[i])
            sphere_mapper = vtk.vtkPolyDataMapper()
            sphere_mapper.SetInputConnection(sphere.GetOutputPort())
            sphere_actor = vtk.vtkActor()
            sphere_actor.SetMapper(sphere_mapper)
            if i==0 or i==6:
                sphere_actor.GetProperty().SetColor(0,0,1)
            else:
                sphere_actor.GetProperty().SetColor(1,1,0)
            self.ren.AddActor(sphere_actor)

        # Create the Renderer
        self.ren.AddActor(iso_actor)
        self.ren.AddActor(frame_actor)
        self.ren.AddActor(frame_actor2)
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

        slider_setup(self.ui.sliderfneg, 0, [0, 100], 10)
        slider_setup(self.ui.sliderfpos, 0, [0, 100], 10)

    def fpos_callback(self, val):
        val = val/100.
        self.coef["fpos"] = val
        self.make_data()

    def fneg_callback(self, val):
        val = val/100.
        self.coef["fneg"] = -val
        self.make_data()

    def make_data(self):
        values = trilinear(self.X, self.Y, self.Z, self.coef)
        self.grid.GetPointData().SetScalars(numpy_support.numpy_to_vtk(values))
        val = trilinear(0.5, 0.5, 0.5, self.coef)
        if val > 0:
            self.sphere_actor.GetProperty().SetColor(1, 1, 0)
        elif val < 0:
            self.sphere_actor.GetProperty().SetColor(0, 0, 1)
        else:
            self.sphere_actor.GetProperty().SetColor(0.5, 0.5, 0.5)
        self.ui.vtkWidget.GetRenderWindow().Render()


if __name__ == "__main__":

    app = QApplication(sys.argv)
    window = SaddleMethod3dDemo()
    window.show()
    window.setWindowState(Qt.WindowMaximized)  # Maximize the window
    window.iren.Initialize() # Need this line to actually show
                             # the render inside Qt

    window.ui.sliderfpos.valueChanged.connect(window.fpos_callback)
    window.ui.sliderfneg.valueChanged.connect(window.fneg_callback)

    sys.exit(app.exec_())
