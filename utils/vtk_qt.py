
try:
    # Try PyQt6 first
    from PyQt6.QtWidgets import QWidget, QMainWindow, QLabel, QPushButton, QTextEdit, QLayout, QGridLayout, QSlider, QHBoxLayout, QVBoxLayout
    from PyQt6.QtCore import Qt
except ImportError:
    # Fall back to PySide6
    try:
        from PySide6.QtWidgets import QWidget, QMainWindow, QLabel, QPushButton, QTextEdit, QLayout, QGridLayout, QSlider, QHBoxLayout, QVBoxLayout
        from PySide6.QtCore import Qt
    except:
        try:
            from PyQt5.QtWidgets import QWidget, QMainWindow, QLabel, QPushButton, QTextEdit, QSlider, QLayout, QGridLayout, QHBoxLayout, QVBoxLayout
            from PyQt5.QtCore import Qt
        except ImportError:
            print("No PyQt/PySide available")
            sys.exit(1)
import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import sys

'''
Convenience functions for PyQt
'''
def slider_setup(slider, val, bounds, interv):
    slider.setOrientation(Qt.Orientation.Horizontal)
    slider.setValue(int(val))
    slider.setTracking(False)
    slider.setTickInterval(interv)
    slider.setTickPosition(QSlider.TickPosition.TicksAbove)
    slider.setRange(bounds[0], bounds[1])

'''
  Our algorithm will run inside a QtVTKProgram, which itself behaves
  as a Qt object with GUI capabilities
'''
class QtVTKProgram(QMainWindow):
    def __init__(self, parent = None):
        QMainWindow.__init__(self, parent)
        # central_widget is the widget that will manage/contain all other widgets
        self.central_widget = QWidget(self) 
        self.setCentralWidget(self.central_widget)
        # We don't have a layout yet 
        self.layout = None

        # That is our VTK widget: a render window and an interactor 
        # wrapped into one. We add it to our main widget.
        self.vtk_widget = QVTKRenderWindowInteractor(self.central_widget)
        # convenience handles for window and interactor
        self.window = self.vtk_widget.GetRenderWindow()
        self.interactor = self.window.GetInteractor()
        # Create renderer and add it to our VTK widget
        self.renderer = vtk.vtkRenderer(gradient_background=True, background=(0.75, 0.75, 0.75))
        self.window.AddRenderer(self.renderer)
        self.frame_counter = 0
        self.frame_basename = 'frame'

    # Layout can either be passed explicitly, or one will be created 
    # by packing the buttons in a column to the right, and the sliders
    # in a row at the bottom, with the VTK window in the top left. 
    # Note: sliders need to be tuples of (label, slider)
    def set_layout(self, layout=None, buttons=[], sliders=[]):
        if layout is not None:
            self.layout = layout
        else:
            self.layout = QGridLayout(self.central_widget)
            # Create button layout
            self.button_layout = QVBoxLayout()
            for b in buttons:
                if isinstance(b, QPushButton):
                    b.setMinimumSize(100, 30)
                    b.setMaximumSize(200, 50)
                elif isinstance(b, QTextEdit):
                    b.setMinimumSize(100, 200)
                    b.setMaximumSize(200, 400)
                else:
                    print(f"Warning: button {b} is not a QPushButton or QLabel")
                self.button_layout.addWidget(b)
            
            # Create slider layout
            self.slider_layout = QHBoxLayout()
            for label, slider in sliders:
                self.slider_layout.addWidget(QLabel(label))
                self.slider_layout.addWidget(slider)

            self.button_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

            self.layout.addWidget(self.vtk_widget, 0, 0, 1, 1)
            self.layout.addLayout(self.slider_layout, 1, 0, 1, 1)
            self.layout.addLayout(self.button_layout, 0, 1, 2, 1)
        self.layout.setParent(self.central_widget)

    # Default callback mechanism
    def draw(self):
        self.window.Render()

    def screenshot_callback(self):
        fname = f"{self.frame_basename}_{self.frame_counter:04d}.jpg"
        image = vtk.vtkWindowToImageFilter()
        image.SetInput(self.window)
        writer = vtk.vtkJPEGWriter(file_name=fname)
        writer.SetInputConnection(image.GetOutputPort())
        self.window.Render()
        writer.Write()
        self.frame_counter += 1
        return fname

    def quit_callback(self):
        sys.exit()