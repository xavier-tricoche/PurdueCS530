#!/usr/bin/env python

import numpy as np
import vtk
from vtk.util import numpy_support as nps
import time
import scipy as sp

np.seterr(all='ignore')

__all__ = [
    'SuperquadricTensorGlyph'
]

def fa(evals):
    return np.sqrt(np.square(evals[:,0]-evals[:,1]) + np.square(evals[:,1]-evals[:,2]) + np.square(evals[:,2]-evals[:,0]))/ np.sqrt(2*(np.square(evals[:,0]) + np.square(evals[:,1]) + np.square(evals[:,2])))

def timer(func):
    t = time.time()
    func()
    return time.time()-t 

class MeshSphere:
    def __init__(self, nlat, nlon=None):
        self.nlat = nlat
        if nlon is None:
            nlon = 2*(nlat-2)
        self.nlon = nlon
        self.angles = []
        self.triangles = []

    # latitudes x longitudes to point index:    
    def c2id(self, lat, lon):
        if lat == 0: # special case of North Pole
            return 0
        elif lat == self.nlat-1: # special case of South Pole
            return 1+(self.nlat-2)*self.nlon
        else:
            return 1+(lat-1)*self.nlon + lon

    def compute_angles(self):
        if len(self.angles) == self.nlat*self.nlon + 2:
            return

        # self.nlon longitudes
        all_thetas = np.linspace(0, 2*np.pi, self.nlon, endpoint=False)
        # self.nlat latitudes + 2 poles
        all_phis = np.linspace(0, np.pi, self.nlat+2, endpoint=True)
        # self.nlat latitudes 
        inner_phis = all_phis[1:-1]
        # self.nlon*self.nlat (longitudes, latitudes) angle pairs
        xx, yy = np.meshgrid(all_thetas, inner_phis)
        self.angles = np.zeros((self.nlon*self.nlat+2, 2), dtype=float)
        inner_angles = np.stack((xx, yy), axis=-1).reshape(-1, 2)
        self.angles[:-2, :] = inner_angles
        self.angles[-2,:] = [0, 0]
        self.angles[-1,:] = [0, np.pi]
        # Convenience ids used during meshing
        self.ids = np.arange(self.nlon*self.nlat).reshape(self.nlat, self.nlon)
        self.south_pole_id = self.nlon*self.nlat 
        self.north_pole_id = self.south_pole_id + 1

    def compute_mesh(self):
        if len(self.triangles) == 2*self.nlon*self.nlat:
            return
        self.compute_angles()

        self.triangles = []
        for j in range(self.nlat-1):
            jj = j+1
            for i in range(self.nlon):
                ii = (i+1)%self.nlon
                self.triangles.append([self.ids[j,i], self.ids[j,ii], self.ids[jj,ii]])
                self.triangles.append([self.ids[j,i], self.ids[jj,ii], self.ids[jj,i]])
        # Circle around South Pole 
        for i in range(self.nlon):
            ii = (i+1)%self.nlon
            self.triangles.append([self.ids[0,i], self.ids[0,ii], self.south_pole_id])
        # Circle around North Pole 
        for i in range(self.nlon):
            ii = (i+1)%self.nlon
            self.triangles.append([self.ids[self.nlat-1,i], self.ids[self.nlat-1,ii], self.north_pole_id])

    def get_angles(self):
        self.compute_angles()
        return np.array(self.angles[:])

    def get_amesh(self, index):
        self.compute_mesh()
        triangles = np.array(self.triangles[:]) # shape = (ntris, 3)
        if index == 0:
            return triangles 
        else:
            offset = (self.nlat*self.nlon + 2)*index
            return triangles + offset

'''
 Superquadric volume formula from:
 A.H. Barr,
 III.8 - RIGID PHYSICALLY BASED SUPERQUADRICS,
 Editor(s): DAVID KIRK,
 Graphics Gems III (IBM Version),
 Morgan Kaufmann,
 1992,
 Pages 137-159,
 ISBN 9780124096738,
 https://doi.org/10.1016/B978-0-08-050755-2.50038-5.

 V_E =  2/3 * alpha * beta * beta_func(alpha/2, alpha/2) * beta_func(beta, beta/2)
 '''
def volumes(alphas, betas):
    return 2./3. * \
        alphas * \
        betas * \
        sp.special.beta(alphas/2, alphas/2) * \
        sp.special.beta(betas, betas/2)

class SQTGlypher:
    '''
    interface required for use with vtkPythonAlgorithm
    '''
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
        
    def __init__(self, resolution=8, gamma=0.5, scale=1, ratio=1, maxfa=1.0, use_vtk=True, verbose=False, translate=True, transform=True, clamp_mode=0) :
        self.res = resolution
        self.gamma = gamma
        self.use_vtk = use_vtk
        self.scale = scale 
        self.ratio = ratio
        self.maxfa = maxfa
        self.maxsize = 1
        self.verbose = verbose
        self.translate=translate 
        self.transform=transform
        self.clamp_mode = 0

    '''
    Compute tensor attributes
    '''
    def compute_tensor_attributes(self):
        tensors = nps.vtk_to_numpy(self.input.GetPointData().GetTensors()).reshape((-1,3,3))
        self.evals, self.evecs = np.linalg.eigh(tensors)
        self.evals[self.evals<0] = 0 # force semi-positive definiteness
        self.dets = np.prod(self.evals, axis=-1)
        self.trace = np.sum(self.evals, axis=-1)
        invtrace = np.where(self.trace==0, 0, 1/self.trace)
        self.ntensors = tensors.shape[0]
        self.cl = (self.evals[:,2]-self.evals[:,1])*invtrace
        self.cp = 2*(self.evals[:,1]-self.evals[:,0])*invtrace
        self.fa = fa(self.evals)
        self.fa[self.fa > 1] = 1
        self.colors = np.absolute(self.evecs[...,2])
        for v in [ self.cl, self.cp, self.fa, self.colors ]:
            v = np.nan_to_num(v, copy=False, nan=0, posinf=0, neginf=0)

        #control saturation and value with FA
        self.colors = self.fa[..., np.newaxis] * (self.fa[..., np.newaxis] * self.colors + (1-self.fa[..., np.newaxis] * np.ones((self.ntensors, 3), dtype=float)))
        # self.colors = (self.fa[..., np.newaxis] * self.colors + (1-self.fa[..., np.newaxis] * np.ones((self.ntensors, 3), dtype=float)))
        self.colors = (255*self.colors).astype(np.uint8)
        self.coords = nps.vtk_to_numpy(self.input.GetPoints().GetData())

    '''
    Apply display ratio
    '''
    def apply_ratio(self):
        self.indices = np.arange(0, self.ntensors)
        if self.ratio is None or self.ratio == 1:
            self.nglyphs = self.ntensors 
            return
        else:
            self.nglyphs = self.ntensors // self.ratio
            rng = np.random.default_rng()
            rng.shuffle(self.indices)
            self.indices = self.indices[:self.nglyphs]
            self.colors = self.colors[self.indices, :]
            self.cl = self.cl[self.indices]
            self.cp = self.cp[self.indices]
            self.evecs = self.evecs[self.indices, :, :]
            self.coords = self.coords[self.indices, :]
            self.evals = self.evals[self.indices, :]
            self.dets = self.dets[self.indices]

    '''
    Compute superquadric coefficients
    '''
    def compute_shapes(self):
        cmin = np.minimum(self.cl, self.cp)
        cmax = np.maximum(self.cl, self.cp)
        self.axes = np.zeros((self.cp.shape), dtype=int)
        self.axes[self.cl<self.cp] = 2
        self.alphas = np.power(1-cmin, self.gamma)
        self.betas = np.power(1-cmax, self.gamma)
        self.alphas[1-cmin < 1.0e-15] = 0
        self.betas[1-cmax < 1.0e-15] = 0

    '''
    Compute superquadrics
    '''
    def compute_superquadrics(self):
        cosines = np.cos(self.angles)
        sines = np.sin(self.angles)
        a = np.power(np.abs(cosines[np.newaxis, :, 0]), self.alphas[:, np.newaxis]) * np.power(np.abs(sines[np.newaxis, :, 1]), self.betas[:, np.newaxis])
        a[:,cosines[:, 0] < 0] *= -1
        a[:,sines[:, 1] < 0] *= -1
        b = np.power(np.abs(sines[np.newaxis, :, 0]), self.alphas[:, np.newaxis]) * np.power(np.abs(sines[np.newaxis, :, 1]), self.betas[:, np.newaxis])
        b[:, sines[:, 0] < 0] *= -1
        b[:, sines[:, 1] < 0] *= -1
        c = np.power(np.abs(cosines[np.newaxis, :, 1]), self.betas[:, np.newaxis])
        c[:, cosines[:, 1] < 0] *= -1
        for v in [a, b, c]:
            v = np.nan_to_num(v, copy=False, nan=0, posinf=0, neginf=0 )

        self.all_points = np.stack((a, b, c), axis=-1)
        isX = self.axes == 0
        self.all_points[isX, :, :] = np.stack((c[isX, :], -b[isX, :], a[isX, :]), axis=-1)
        self.all_points *= self.scale

        # create mesh topology
        self.mesh.compute_mesh()
        ntriangles = len(self.mesh.triangles)

        all_triangles = np.zeros((self.nglyphs, ntriangles, 3), dtype=np.int64)
        all_offsets = np.arange(self.nglyphs*ntriangles+1, dtype=np.int64)*3
        for n in range(self.nglyphs):
            all_triangles[n,:,:] = self.mesh.get_amesh(n)
        self.cells = vtk.vtkCellArray()
        self.cells.SetData(nps.numpy_to_vtk(all_offsets), nps.numpy_to_vtk(all_triangles.ravel()))

    '''
    Enforce self.maxsize upper bound on glyph volumes
    '''
    def clamp_size(self):
        if self.clamp_mode == 0:
            # Enforce upper bound on superquadric glyph volume
            self.sizes = self.dets * self.scale * self.scale * self.scale * volumes(self.alphas, self.betas)
            correction = np.power(self.sizes/self.maxsize, 1/3)
        elif self.clamp_mode == 1:
            # Enforce upper bound on superquadric length
            self.sizes = self.scale * self.evals[...,2]
            correction =  self.sizes/self.maxsize 
        elif self.clamp_mode == 2:
            # Enforce upper bound on superquadric diameter
            self.sizes = self.scale * np.linalg.norm(self.evals, axis=-1)
            correction = self.sizes / self.maxsize

        too_large = self.sizes > self.maxsize 
        self.evals[too_large, :] /= correction[too_large, np.newaxis]


    '''
    Compute linear transforms associated with tensor shape
    '''
    def compute_xforms(self):
        # Convert triplets of eigenvalues into 3x3 diagonal matrices
        to_diag = np.vectorize(np.diag, signature='(n)->(n,n)')
        Lambda = to_diag(self.evals)
        # Compute glyph transformation matrices
        self.evecs = np.matmul(self.evecs, Lambda)

    '''
    Apply linear transformations (anisotropic scaling and rotation) to all 
    glyphs
    '''
    def apply_xforms(self):
        if self.transform and self.translate:
            self.all_points = np.matvec(self.evecs[:, np.newaxis, :, [2,1,0]], self.all_points) + self.coords[:, np.newaxis, :]
        elif self.transform:
            self.all_points = np.matvec(self.evecs[:, np.newaxis, :, [2,1,0]], self.all_points)
        elif self.translate:
            self.all_points += self.coords[:, np.newaxis, :]
        self.output.GetPoints().SetData(nps.numpy_to_vtk(self.all_points.reshape((-1, 3))))

    '''
    Compute all the tensor attributes and superquadrics parameters needed
    to generate glyphs
    '''
    def Update(self):
        if self.verbose: init = time.time()
        self.mesh = MeshSphere(self.res)
        self.angles = self.mesh.get_angles()
        self.npoints = self.angles.shape[0]

        tensor_t = timer(self.compute_tensor_attributes)
        ratio_t = timer(self.apply_ratio)
        shape_t = timer(self.compute_shapes)
        size_t = timer(self.clamp_size)
        xforms_t = timer(self.compute_xforms)

        t = time.time()
        pts = vtk.vtkPoints()
        self.output.SetPoints(pts)
        self.compute_superquadrics()
        self.output.SetPolys(self.cells)
        if self.verbose: 
            super_t = time.time()-t

        # do all transforms at once
        if self.transform or self.translate:
            apply_x_t = timer(self.apply_xforms)
        else:
            apply_x_t = 0
            
        self.output.GetPointData().SetScalars(nps.numpy_to_vtk(np.tile(self.colors, (1,self.npoints)).reshape((-1, 3))))

        if self.verbose:
            total_t = time.time() - init
            print(f'stats:')
            print(f' * total time: {total_t}')
            print(f' * tensor attributes: {tensor_t} ({tensor_t/total_t*100:.1f}%)')
            print(f' * subset selection: {ratio_t} ({ratio_t/total_t*100:.1f}%)')
            print(f' * Shape parameters: {shape_t} ({shape_t/total_t*100:.1f}%)')
            print(f' * size claming: {size_t} ({size_t/total_t*100:.1f}%)')
            print(f' * linear xforms: {xforms_t} ({xforms_t/total_t*100:.1f}%)')
            print(f' * superquadrics: {super_t} ({super_t/total_t*100:.1f}%)')
            print(f' * transform time: {apply_x_t} ({apply_x_t/total_t*100:.1f}%)')


class SuperquadricTensorGlyph(vtk.vtkPythonAlgorithm):
    def __init__(self):
        vtk.vtkPythonAlgorithm.__init__(self)
        self.sqa = SQTGlypher()
        self.SetPythonObject(self.sqa)

    def SetInputData(self, data):
        self.SetInputDataObject(0, data)

    def SetGamma(self, gamma):
        self.sqa.gamma = gamma 
        self.Modified()

    def GetGamma(self):
        return self.sqa.gamma 
    
    def SetResolution(self, resolution):
        self.sqa.res = resolution 
        self.Modified()

    def GetResolution(self):
        return self.sqa.res

    def SetDisplayRatio(self, ratio):
        self.sqa.ratio = ratio 
        self.Modified()

    def GetDisplayRatio(self):
        return self.sqa.ratio
    
    def SetScale(self, scale):
        self.sqa.scale = scale 
        self.Modified()

    def GetScale(self):
        return self.sqa.scale
    
    def SetMaxSize(self, maxsize):
        self.sqa.maxsize = maxsize
        self.Modified()

    def GetMaxSize(self):
        return self.sqa.maxsize

    def SetClampingMode(self, mode):
        self.sqa.clamp_mode = mode 

    def GetClampingMode(self):
        return self.sqa.clamp_mode

    def SetClampingModeToVolume(self):
        self.sqa.clamp_mode = 0

    def SetClampingModeToLength(self):
        self.sqa.clamp_mode = 1 

    def SetClampModeToDiameter(self):
        self.sqa.clamp_mode = 2
    
    def GetMaxFA(self):
        return self.sqa.maxfa 
    
    def SetMaxFA(self, mfa):
        self.sqa.maxfa = mfa
        self.Modified()
    
    def GetOutput(self):
        return vtk.vtkPolyData.SafeDownCast(vtk.vtkPythonAlgorithm.GetOutputDataObject(self, 0))

    def SetVerbosity(self, verbose=True):
        self.sqa.verbose = verbose

    def GetVerbosity(self):
        return self.sqa.verbose