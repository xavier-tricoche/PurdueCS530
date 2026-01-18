import vtk
import os

'''
   Useful functions when working with VTK
'''

__all__ = [
    connect,
    correct_reader,
    correct_writer,
]

def is_algorithm(object):
    return isinstance(object, vtk.vtkAlgorithm)

def is_dataset(object):
    return isinstance(object, vtk.vtkDataSet)

def connect(input, output):
    if is_algorithm(input) and is_algorithm(output):
        output.SetInputConnection(input.GetOutputPort())
    elif is_dataset(input) and is_algorithm(output):
        output.SetInputData(input)
    else:
        raise TypeError(f'Invalid types {type(input)} / {type(output)} in connect')
    return output

def replace_extension(filename, ext):
    if ext[0] == '.':
        ext = ext[1:]
    name, removed = os.path.splitext(filename)
    return os.path.join(name, ext)

def correct_reader(filename, _ext=None):
    if _ext is not None:
        filename = replace_extension(filename, _ext)
    name, ext = os.path.splitext(filename)
    reader = None
    if ext == '.vtk' or ext == '.VTK':
        reader = vtk.vtkDataSetReader()
    elif ext == '.vti' or ext == '.VTI':
        reader = vtk.vtkXMLImageDataReader()
    elif ext == '.vtu' or ext == '.VTU':
        reader = vtk.vtkXMLUnstructuredGridReader()
    elif ext == '.vtp' or ext == '.VTP':
        reader = vtk.vtkXMLPolyDataReader()
    elif ext == '.vtr' or ext == '.VTR':
        reader = vtk.vtkXMLRectilinearGridReader()
    else:
        print('unrecognized vtk filename extension: ', ext)
        return None
    reader.SetFileName(filename)
    return reader

def correct_writer(filename, _ext=None):
    if _ext is not None:
        filename = replace_extension(filename, _ext)
    name, ext = os.path.splitext(filename)
    writer = None
    if ext == '.vtk' or ext == '.VTK':
        writer = vtk.vtkDataSetWriter()
    elif ext == '.vti' or ext == '.VTI':
        writer = vtk.vtkXMLImageDataWriter()
    elif ext == '.vtu' or ext == '.VTU':
        writer = vtk.vtkXMLUnstructuredGridWriter()
    elif ext == '.vtp' or ext == '.VTP':
        writer = vtk.vtkXMLPolyDataWriter()
    elif ext == '.vtr' or ext == '.VTR':
        writer = vtk.vtkXMLRectilinearGridWriter()
    else:
        print('unrecognized vtk filename extension: ', ext)
        return None
    writer.SetFileName(filename)
    return writer
