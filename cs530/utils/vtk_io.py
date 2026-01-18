import os
import vtk

'''
Helper functions to import and export various VTK data formats
'''

__all__ = [
    'read_vtk_file', 
    'save_vtk_file'
]

def __write(writer_type, input, filename):
    writer = writer_type(file_name=filename)
    if isinstance(input, vtk.vtkAlgorithm):
        writer.SetInputConnection(input.GetOutputPort())
    else:
        writer.SetInputData(input)
    writer.Write()

def replace_extension(filename, newext):
    return os.path.splitext(filename)[0] + newext

def read_vtk_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.vtk':
        return vtk.vtkDataSetReader(file_name=filename)
    elif ext == '.vti':
        return vtk.vtkXMLImageDataReader(file_name=filename)
    elif ext == '.vtu':
        return vtk.vtkXMLUnstructuredGridReader(file_name=filename)
    elif ext == '.vtp':
        return vtk.vtkXMLPolyDataReader(file_name=filename)
    elif ext == '.vtr':
        return vtk.vtkXMLRectilinearGridReader(file_name=filename)
    elif ext == '.jpg' or ext == '.jpeg':
        return vtk.vtkJPEGReader(file_name=filename)
    elif ext == '.png':
        return vtk.vtkPNGReader(file_name=filename)
    elif ext == '.tif' or ext == '.tiff':
        return vtk.vtkTIFFReader(file_name=filename)
    elif ext == '.nrrd' or ext == '.nhdr':
        return vtk.vtkNrrdReader(file_name=filename)
    elif ext == '.csv':
        return vtk.vtkDelimitedTextReader(file_name=filename)
    else:
        raise TypeError(f'Unrecognized VTK file extension {ext}')

def save_vtk_file(dataset, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.vtk':
        return __write(vtk.vtkDataSetWriter, dataset, filename)
    elif ext == '.vti':
        return __write(vtk.vtkXMLImageDataWriter, dataset, filename)
    elif ext == '.vtu':
        return __write(vtk.vtkXMLUnstructuredGridWriter, dataset, filename)
    elif ext == '.vtp':
        return __write(vtk.vtkXMLPolyDataWriter, dataset, filename)
    elif ext == '.vts':
        return __write(vtk.vtkXMLStructuredGridWriter, dataset, filename)
    elif ext == '.vtr':
        return __write(vtk.vtkXMLRectilinearGridWriter, dataset, filename)
    elif ext == '.jpg' or ext == '.jpeg':
        return __write(vtk.vtkJPEGWriter, filename)
    elif ext == '.png':
        return __write(vtk.vtkPNGWriter, filename)
    elif ext == '.tif' or ext == '.tiff':
        return __write(vtk.vtkTIFFWriter, filename)
    elif ext == '.csv':
        return __write(vtk.vtkDelimitedTextWriter, filename)
    else:
        raise ValueError(f'Unrecognized VTK file extension: {ext}')

def saveVTK_XML(dataset, filename):
    if isinstance(dataset, vtk.vtkImageData):
        filename = replace_extension(filename, '.vti')
    elif isinstance(dataset, vtk.vtkUnstructuredGrid):
        filename = replace_extension(filename, '.vtu')
    elif isinstance(dataset, vtk.vtkPolyData):
        filename = replace_extension(filename, '.vtp')
    elif isinstance(dataset, vtk.vtkRectilinearGrid):
        filename = replace_extension(filename, '.vtr')
    elif isinstance(dataset, vtk.vtkStructuredGrid):
        filename = replace_extension(filename, '.vts')
    else:
        filename = replace_extension(filename, '.vtk')
        print('WARNING: Unrecognized VTK dataset type. Using Legacy format')

    print(f'filename is {filename}')
    saveVTK(dataset, filename)
