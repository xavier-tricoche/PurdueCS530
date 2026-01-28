import scipy.integrate
import vtk
import numpy as np
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy
import argparse
from random import *
import os
import nrrd
import scipy
import time
from collections import deque

__all__ = [
    'Interpolator', 
    'TimeInterpolator'
]

class _Utils:
    # flatten an array of arrays of numpy arrays
    @staticmethod
    def _flatten(v):
        if len(v) == 0: return v 
        elif isinstance(v[0], np.ndarray) or not isinstance(v[0], (list, tuple)):
            return v
        else: return [ item for item in sublist for sublist in v ]

    @staticmethod
    def _singleton_as_scalar(v):
        if len(v) == 1: return v[0]
        else: return v
    
    @staticmethod
    def _singleton_as_array(v):
        if not isinstance(v, list): return [v]
        else: return v

    @staticmethod
    def _as_numpy(v):
        if isinstance(v, vtk.vtkDataArray): return vtk_to_numpy(v)
        else: return v

    @staticmethod
    def _import_dataset(filename):
        ext = os.path.splitext(filename)[1].lower()
        # note: .vtp is invalid here
        match ext:
            case '.vtk':
                reader = vtk.vtkDataSetReader(file_name=filename)
                reader.Update()
                return reader.GetOutput()
            case '.vtu':
                reader = vtk.vtkXMLUnstructuredGridReader(file_name=filename)
                reader.Update()
                return reader.GetOutput()
            case '.vti':
                reader = vtk.vtkXMLImageDataReader(file_name=filename)
                reader.Update()
                return reader.GetOutput()
            case '.vtr':
                reader = vtk.vtkXMLRectilinearGridReader(file_name=filename)
                reader.Update()
                return reader.GetOutput()
            case '.vts':
                reader = vtk.vtkXMLStructuredGridReader(file_name=filename)
                reader.Update()
                return reader.GetOutput()
            case '.nrrd':
                data, header = nrrd.read(filename)
                # TODO: handle header
                return None
            case _:
                raise ValueError(f'Unrecognized or unsupported file type: {filename}')

    @staticmethod
    def _get_attribute(dataset, name):
        if name.lower() == 'scalar' or name.lower() == 'scalars':
            return dataset.GetPointData().GetScalars()
        elif name.lower() == 'vector' or name.lower() == 'vectors':
            return dataset.GetPointData().GetVectors()
        elif name.lower() == 'tensor' or name.lower() == 'tensors':
            return dataset.GetPointData().GetTensors()
        else:
            return dataset.GetPointData().GetArray(name)

    @staticmethod
    def _locate(locator, p):
        acell = vtk.vtkGenericCell()
        subid = vtk.reference(0)
        pcoords = np.zeros(3)
        weights = np.zeros(8)
        cellpts = vtk.vtkIdList()
        has_explicit_locator = isinstance(locator, vtk.vtkAbstractCellLocator)
        if has_explicit_locator:
            cellid = locator.FindCell(p, 0, acell, subid, pcoords, weights)
        else:
            cellid = locator.FindCell(p, None, 0, 0.0, subid, pcoords, weights)
        if cellid == -1:
            raise ValueError(f'Position {p} is not in dataset domain')
        else:
            if has_explicit_locator:
                locator.GetDataSet().GetCellPoints(cellid, cellpts)
            else:
                locator.GetCellPoints(cellid, cellpts)
        return cellid, cellpts, weights

    @staticmethod
    def _nbytes(fields):
        return np.sum([field.nbytes for field in fields])

class InterpolatorBase:
    def __init__(self, vtk_data, raise_oob_error=False):
        self.data = vtk_data
        self.oob_error = raise_oob_error
        if isinstance(self.data, vtk.vtkPointSet):
            # dataset has explicit coordinates representation
            # non-trivial point location case
            self.locator = vtk.vtkCellTreeLocator()
            self.locator.SetDataSet(self.data)
            self.locator.BuildLocator()
        elif isinstance(self.data, vtk.vtkImageData) or isinstance(self.data, vtk.vtkRectilinearGrid):
            self.locator = self.data
        else:
            raise ValueError('Unrecognized dataset type')

    def interpolate(self, p, fields):
        _fields = _Utils._singleton_as_array(fields)
        p = np.array(p)
        try:
            _, cellpts, weights = _Utils._locate(self.locator, p)
        except ValueError as e:
            if self.oob_error:
                raise e
            else:
                return None
        vals = [ np.zeros(f.shape[1]) for f in _fields ]
        for i in range(cellpts.GetNumberOfIds()):
            id = cellpts.GetId(i)
            for j, f in enumerate(_fields):
                vals[j] += weights[i] * f[id]
        return _Utils._singleton_as_scalar([_Utils._singleton_as_scalar(v) for v in vals])

class Interpolator(InterpolatorBase):
    def __init__(self, vtk_data, fields, raise_oob_error=False):
        super().__init__(vtk_data, raise_oob_error)
        self.set_fields(fields)

    def set_fields(self, fields):
        self.fields = [ _Utils._as_numpy(f) for f in _Utils._singleton_as_array(fields) ]
        self.nbytes = _Utils._nbytes(self.fields)

    def __call__(self, t, p):
        return self.interpolate(p, self.fields)

class TimeInterpolator(InterpolatorBase):

    def __init__(self, times, filenames, attributes=['vectors'], stack=3, raise_oob_error=False):
        super().__init__(import_dataset(filenames[0]), raise_oob_error)
        ids = np.argsort(times)
        self.filenames = [filenames[i] for i in ids]
        self.times = [times[i] for i in ids]
        self.field_names = attributes
        self.stack = stack 
        self.cached_fields = deque()
        self.cached_time_steps = deque()
        self.nfields = len(self.field_names)

    def load(self, ids, _case):
        if _case == 'full':
            for id in ids:
                dataset = _Utils._import_dataset(self.filenames[id])
                fields = [ _Utils._as_numpy(dataset.GetPointData().GetArray(name)) for name in self.field_names ]
                self.cached_fields.append(fields)
                self.cached_time_steps.append(id)
        elif _case == 'left':
            for id in ids:
                self.cached_fields.pop()
                self.cached_time_steps.pop()
                dataset = _Utils._import_dataset(self.filenames[id])
                fields = [ _Utils._as_numpy(dataset.GetPointData().GetArray(name)) for name in self.field_names ]
                self.cached_fields.appendleft(fields)
                self.cached_time_steps.appendleft(id)
        elif _case == 'right':
            for id in ids:
                self.cached_fields.popleft()
                self.cached_time_steps.popleft()
                dataset = _Utils._import_dataset(self.filenames[id])
                fields = [ _Utils._as_numpy(dataset.GetPointData().GetArray(name)) for name in self.field_names ]
                self.cached_fields.append(fields)
                self.cached_time_steps.append(id)

    def update(self, i, hint='centered'):
        # find i such that t_{i-1} <= t < t_i
        if i == 0 or i == len(self.times):
            raise ValueError(f"Time {t} is out of bounds [{self.times[0]}, {self.times[-1]}]")
        # currently cached time span
        if len(self.cached_time_steps) > 0:
            jmin = self.cached_time_steps[0]
            jmax = self.cached_time_steps[-1] 
        else:
            jmin = 0
            jmax = 0
        # compute desired bounds
        if hint == 'forward':
            n0 = 1
            n1 = self.stack-1
        elif hint == 'backward':
            n1 = 0
            n0 = self.stack+1
        else: # balanced/centered
            n0 = self.stack//2 
            n1 = self.stack-n0
        imin = max(i-n0, 0)
        imax = min(i+n1, len(self.times)) 
        if imin == 0: imax = min(self.stack-1, len(self.times)-1)
        if imax == len(self.times)-1: imin = max(len(self.times)-self.stack, 0)
        if jmax <= jmin or imin > jmax or imax < jmin:
            # no overlap: (re)load full stack
            self.load(np.arange(imin, imax), 'full')
        elif imin < jmin:
            # extend left
            self.load(np.arange(imin, jmin), 'left')
        elif imax > jmax:
            # extend right
            self.load(np.arange(jmax+1, imax+1), 'right')
        # otherwise, nothing to do.

    def fetch(self, t):
        i = np.searchsorted(self.times, t)
        if len(self.cached_times) == 0:
            self.update(i, 'centered')
        elif i < self.cached_times[0]:
            self.update(i, 'left')
        elif i > self.cached_times[-1]:
            self.update(i, 'right')
        j = np.searchsorted(self.cached_time_steps, i, side='right')
        u = (t - self.cached_times[j-1]) / (self.cached_times[j] - self.cached_times[j-1])
        return u, self.cached_fields[j-1], self.cached_fields[j]

    def __call__(self, t, p):
        if t < self.times[0] or t > self.times[-1]:
            raise ValueError(f'Time {t} outside of temporal range {self.times[0]} - {self.times[-1]}')

        u, f0, f1 = self.fetch(t)
        all_fields = [ f for f in fields for fields in [f0, f1]]
        try:
            values = self.interpolate(p, all_fields)
            if values is not None:
                if self.nfields == 1: return (1-u)*values[0] + u*values[1]
                else: return [ (1-u)*values[i] + u*values[i+self.nfields] for i in range(self.nfields) ]
        except Exception as e:
            print(f'Error interpolating at {p}: {e}')
            raise e

def main():
    parser = argparse.ArgumentParser(description='Test RHS wrapper for VTK datasets')
    parser.add_argument('-i', '--input', required=True, help='Input dataset')
    parser.add_argument('-f', '--field', required=True, help='Field to interpolate')
    parser.add_argument('-n', '--number', default=1, help='Number of interpolations to perform')
    args = parser.parse_args()

    data = import_dataset(args.input)
    print(data)
    field = get_attribute(data, args.field)
    print(field)
    intp = Interpolator(data, field)

    xmin, xmax, ymin, ymax, zmin, zmax = data.GetBounds()
    pmin = np.array([xmin, ymin, zmin])
    pmax = np.array([xmax, ymax, zmax])
    print(f'mins: {pmin}')
    print(f'maxes: {pmax}')

    MAX_TIMESTAMP = 11
    INITIAL_INDEX = 200000

    filenames = []
    for i in range(1, MAX_TIMESTAMP):
        timestamp = ""
        if (i < 10):
                timestamp = '0' + str(i)
        else:
            timestamp = str(i)
        filenames.append('velocity/velocity_' + timestamp + '.vti')
    #print(filenames)
    tintp = TimeInterpolator([i for i in range(1, MAX_TIMESTAMP)], filenames)

    for i in range(args.number):
        x = random()
        y = random()
        z = random()
        t = random() + 1
        p = np.array([x,y,z])
        p = (np.ones(3)-p)*pmin + p*pmax
        try:
            value = intp(0, p)
            print(f'value at {p} is {value}')
            time_pos_val = tintp(t, p)
            print(f'vector at {value} at time {t} is {time_pos_val}')
        except ValueError:
            print(f'position {p} lies outside domain boundary')
    y0 : vtk.vtkTypeFloat32Array = get_attribute(import_dataset(filenames[1]), 'vectors')
    intitial_value = (1000,1000,10)
    print(f'value of intitial value: {intitial_value}')
    result = scipy.integrate.solve_ivp(tintp, (1.01, MAX_TIMESTAMP - 1), intitial_value, dense_output=True)
    time_points = result['t']
    y = result['y']
    sol : scipy.integrate.OdeSolution = result['sol']
    success = result['success']
    print(f'Time points: {time_points}, y: {y}, sol: {sol}, success: {success}')
    print([sol(i) for i in range(1, 1000)])

if __name__ == '__main__':
    main()
