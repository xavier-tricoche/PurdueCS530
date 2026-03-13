import numpy as np
import scipy as sp
from scipy import integrate as intg
import vtk
from vtk.util import numpy_support as nps
import math
import time
from tqdm import tqdm

__all__ = [
    'TensorLines',
    'RHS'
]

class Interpolator:
    def __init__(self, dataset):
        self.dataset = dataset 
        self.locator = None
        bnds = self.dataset.GetBounds()
        self.bounds = [ np.array([bnds[0], bnds[2], bnds[4]]), 
                        np.array([bnds[1], bnds[3], bnds[5]]) ]
        if isinstance(self.dataset, vtk.vtkImageData):
            self.is_image = True 
            self.dims = np.array(dataset.GetDimensions())
            self.origin = np.array(dataset.GetOrigin())
            self.spacing = np.array(dataset.GetSpacing())
            self.tensors = nps.vtk_to_numpy(dataset.GetPointData().GetTensors()).reshape((self.dims[2], self.dims[1], self.dims[0], 9))
        else:
            self.is_image = False 
            self.locator = vtk.vtkCellTreeLocator()
            self.locator.SetDataSet(self.data)
            self.locator.BuildLocator()

    def interpolate_image(self, pos):
        x = (pos-self.origin)/self.spacing
        cellid = np.floor(x)
        if np.any(x < 0) or np.any(cellid > self.dims-2):
            raise RuntimeError('Invalid position')
        u, v, w = x - cellid
        i, j, k = cellid.astype(int)
        T  = ((1-u)*(1-v)*(1-w))*self.tensors[  k,   j,   i, :] + \
             (   u *(1-v)*(1-w))*self.tensors[  k,   j, 1+i, :] + \
             (   u *   v *(1-w))*self.tensors[  k, 1+j, 1+i, :] + \
             ((1-u)*   v *(1-w))*self.tensors[  k, 1+j,   i, :] + \
             ((1-u)*(1-v)*   w )*self.tensors[1+k,   j,   i, :] + \
             (   u *(1-v)*   w )*self.tensors[1+k,   j, 1+i, :] + \
             (   u *   v *   w )*self.tensors[1+k, 1+j, 1+i, :] + \
             ((1-u)*   v *   w )*self.tensors[1+k, 1+j,   i, :]
        return T.reshape(3, 3)

    def interpolate(self, pos):
        cellid = self.locator.FindCell(p)
        if cellid == -1:
            raise ValueError('Invalid Position')
        cell = self.data.GetCell(cellid)
        weights = np.zeros((8), dtype=float)
        pcoords = np.zeros((3), dtype=float)
        closest = np.zeros((3), dtype=float)
        subId = vtk.reference(0)
        dist = vtk.reference(0)
        cell.EvaluatePosition(p, closest, subId, pcoords, dist, weights)
        T = np.zeros((9), dtype=float)
        for i in range(cell.GetNumberOfPoints()):
            pid = cell.GetPointId(i)
            T += weights[i] * np.array(self.data.GetPointData().GetTensors().GetTuple9(pid))
        return T.reshape(3,3)

    def __call__(self, pos):
        if self.is_image:
            return self.interpolate_image(pos)
        else:
            return self.interpolate(pos)


'''
Direction (vector) to color
'''
def vec_to_color(vec, normalize=False, saturation=1):
    saturation = max(0, min(saturation, 1))
    vec = np.absolute(vec)
    if normalize:
        vec /= np.linalg.norm(vec)
    return saturation*vec + (1-saturation)*np.ones(3)

'''
Curve to colors
'''
def curve_to_colors(curve, FA=None):
    curve = np.array(curve)
    length = curve.shape[0]
    if FA is not None:
        saturations = np.array(FA)
        saturations[saturations<0] = 0
        saturations[saturations>1] = 1
    tangents = np.zeros_like(curve)
    tangents[1:-1,:] = curve[2:,:] - curve[:-2,:]
    tangents[0,:] = curve[1]-curve[0]
    tangents[-1,:] = curve[-1]-curve[-2]
    tangents /= np.linalg.norm(tangents, axis=-1)[:, np.newaxis]
    tangents = np.absolute(tangents)
    if FA is None:
        colors = np.absolute(tangents)
    else:
        colors = saturations[:, np.newaxis] * tangents + (1-saturations)[:, np.newaxis] * np.ones_like(curve)
    return (255*colors).astype(np.uint8)

'''
Eigendecomposition of symmetric tensor
'''
def symeigendec(T, only_evals = False):
    return sp.linalg.eigh(T, eigvals_only=only_evals)

'''
Fractional Anisotropy Formula
'''
def FA(l0, l1, l2):
    num = (l0-l1)*(l0-l1) + (l1-l2)*(l1-l2) + (l2-l0)*(l2-l0)
    den = 2*(l0*l0 + l1*l1 + l2*l2)
    if den == 0:
        return 0
    else:
        return math.sqrt(num/den)


'''
Vector field interface to major eigenvector field of symmetric tensor field
'''
class RHS:
    def __init__(self, data, minFA=0.3):
        self.interpolator = Interpolator(data)
        self.data = data
        self.bounds = self.interpolator.bounds
        self.last = None
        self.sign = 1
        self.minFA = minFA

    def lower_bound_FA(self, t, y):
        T = self.interpolator(y)
        evs = symeigendec(T, True)
        v = FA(evs[0], evs[1], evs[2])
        return v - self.minFA

    def reset(self):
        self.last = None
        self.sign = 1

    def value(self, pos):
        return self.interpolator(pos)

    def FA(self, pos):
        try:
            T = self.value(pos)
        except Exception as e:
            return 0
        evals = symeigendec(T, True)
        try:
            return FA(evals[0], evals[1], evals[2])
        except:
            return 0

    '''
    Interpolating functor
    '''
    def __call__(self, t, pos):
        try:
            T = self.value(pos)
        except Exception as e:
            return np.array([0,0,0])
        evs, evecs = symeigendec(T)
        d = 1
        if self.last is None:
            self.last = self.sign*evecs[:,2]
        else:
            d = np.dot(self.last, evecs[:,2])
            if d < 0:
                self.last = -1 * evecs[:,2]
            else:
                self.last = evecs[:,2]
        return self.last

class FAUnderflowEvent:
    def __init__(self, rhs, minFA):
        self.rhs = rhs 
        self.minFA = minFA 
        self.terminal = True

    def __call__(self, t, y):
        return self.rhs.FA(y) >= self.minFA

class OutOfDomainEvent:
    def __init__(self, rhs):
        self.bounds = rhs.bounds 
        self.terminal = True

    def __call__(self, t, y):
        # bmin <= y <= bmax
        test1 = y-self.bounds[0]
        test2 = self.bounds[1]-y 
        return min(np.min(test1), np.min(test2))

class TLine:
    def Initialize(self, vtkself):
        vtkself.SetNumberOfInputPorts(1)
        vtkself.SetNumberOfOutputPorts(1)

    def FillInputPortInformation(self, vtkself, port, info):
        info.Set(vtk.vtkAlgorithm.INPUT_REQUIRED_DATA_TYPE(), "vtkDataSet")
        return 1

    def FillOutputPortInformation(self, vtkself, port, info):
        info.Set(vtk.vtkDataObject.DATA_TYPE_NAME(), "vtkPolyData")
        return 1
    
    def ProcessRequest(self, vtkself, request, inInfo, outInfo):
        if request.Has(vtk.vtkDemandDrivenPipeline.REQUEST_DATA()):
            self.input = vtk.vtkDataSet.GetData(inInfo[0])
            self.output = vtk.vtkPolyData.GetData(outInfo)
            self.Update()
        return 1
    
    def SetSource(self, source):
        self.source = source

    def SetMinFA(self, minFA):
        self.minFA = minFA

    def SetMaxLength(self, maxlength):
        self.length = maxlength

    def SetMaxNumberOfSteps(self, maxnsteps):
        self.nsteps = maxnsteps

    def SetStepSize(self, dh):
        self.stepsize = dh

    def __init__(self, source=None, stepsize=1, length=100, nsteps=500, 
                 minFA=0.3, control_saturation=False):
        self.source = source
        self.stepsize = stepsize
        self.length = length 
        self.nsteps = nsteps
        self.minFA = minFA
        self.control_saturation = control_saturation
        self.rtol = 1.0e-3
        self.atol = 1.0e-3

    def integrate(self, seed, direction):
        if self.source is None:
            raise ValueError('No source available for TensorLines')

        self.rhs.reset()
        if direction < 0:
            self.rhs.sign = -1

        steps = np.linspace(0, self.length, int(self.length/self.stepsize))

        t0 = time.process_time()
        sol = intg.solve_ivp(self.rhs, y0=seed, rtol=self.rtol, atol=self.atol, first_step=self.stepsize, max_step=self.nsteps, t_span=[0, self.length], t_eval=steps, method='RK45', events=[self.fa_event, self.out_event])
        traj = sol.y.T

        t1 = time.process_time()

        if len(traj) <= 50:
            return None, None, t1-t0, 0

        if self.control_saturation:
            fas = []
            for p in traj:
                fas.append(self.rhs.FA(p))
            colors = np.array(curve_to_colors(traj, fas))
        else:
            colors = np.array(curve_to_colors(traj))
        return traj, colors, t1-t0, time.process_time()-t1
        
    def Update(self):
        if self.source is None:
            raise Exception('No source provided in TensorLine')
        elif not isinstance(self.source, vtk.vtkDataSet):
            raise Exception('Source is not a vtkDataSet in TensorLine')
        
        self.rhs = RHS(self.input, minFA=self.minFA)
        self.fa_event = FAUnderflowEvent(self.rhs, self.minFA)
        self.out_event = OutOfDomainEvent(self.rhs)
        pts = self.source.GetPoints()
        all_lines = vtk.vtkCellArray()
        all_coords = []
        all_colors = []
        t_integrate = 0
        t_color = 0
        n_integrate = 0
        n_color = 0
        t0 = time.process_time()
        for i in tqdm(range(pts.GetNumberOfPoints()), desc='Integration'):
            p = np.array(pts.GetPoint(i))
            for adir in [ 1, -1 ]:
                points, colors, dt_integrate, dt_color = self.integrate(p, adir)
                t_integrate += dt_integrate
                if dt_integrate != 0:
                    n_integrate += 1
                t_color += dt_color
                if dt_color != 0:
                    n_color += 1

                if points is not None and points.shape[0] > 50:
                    n = points.shape[0]
                    k = len(all_coords)
                    all_coords.extend(points.tolist())
                    all_lines.InsertNextCell(n, np.arange(k, k+n))
                    all_colors.extend(colors.tolist())
        t1 = time.process_time()
        print(f'{all_lines.GetNumberOfCells()} fibers integrated in {t1-t0} seconds ({float(all_lines.GetNumberOfCells())/(t1-t0)} Hz.)')
        print(f'integration time: {t_integrate} s. ({t_integrate/(t1-t0)*100}% / {float(n_integrate)/t_integrate} Hz.), coloring time: {t_color} s. ({t_color/(t1-t0)*100}% / {float(n_color)/t_color} Hz.)')
        vtkpts = vtk.vtkPoints()
        vtkpts.SetData(nps.numpy_to_vtk(np.array(all_coords)))
        self.output.SetPoints(vtkpts)
        self.output.SetLines(all_lines)
        self.output.GetPointData().SetScalars(nps.numpy_to_vtk(np.array(all_colors, dtype=np.uint8)))

class TensorLines(vtk.vtkPythonAlgorithm):
    def __init__(self):
        vtk.vtkPythonAlgorithm.__init__(self)
        self.tline = TLine()
        vtk.vtkPythonAlgorithm.SetPythonObject(self, self.tline)

    def SetSource(self, source):
        self.tline.SetSource(source) 
        self.Modified()

    def SetIntegrationLength(self, length):
        self.tline.SetLength(length)
        self.Modified()

    def SetStepSize(self, ssize):
        self.tline.SetStepSize(ssize)
        self.Modified()

    def SetMinFA(self, minfa):
        self.tline.SetMinFA(minfa)

    def SetMaxNumberOfSteps(self, nsteps):
        self.tline.SetMaxNumberOfSteps(nsteps)

    def SetMaxLength(self, length):
        self.tline.SetMaxLength(length)

    def SetIntegrationPrecision(self, reltol, abstol=None):
        self.tline.reltol = reltol 
        if abstol is not None:
            self.tline.abstol = abstol 
        else:
            self.tline.abstol = reltol
    
    def GetOutput(self):
        return vtk.vtkPolyData.SafeDownCast(vtk.vtkPythonAlgorithm.GetOutputDataObject(self, 0))

    def SetControlSaturation(self, do_control):
        self.tline.control_saturation = do_control
    
    def ControlSaturationOn(self):
        self.tline.control_saturation = True 

    def ControlSaturationOff(self):
        self.tline.control_saturation = False
