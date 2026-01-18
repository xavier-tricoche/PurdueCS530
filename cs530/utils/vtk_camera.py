import vtk
import json
import os
import time

'''

Helper functions to import/export and print out camera and light settings

'''

__all__ = [
    'save_camera',
    'load_camera',
    'print_camera',
    'save_light',
    'load_lights',
    'print_light',
]

# for fully reproducible results, the window size is needed
def save_camera(camera=None, renderer=None, filename='camera.json'):
    if camera is None:
        if renderer is not None:
            camera = renderer.GetActiveCamera()
        else:
            raise ValueError('Missing camera input')
    cam = { 'position': camera.position, 
            'focal_point': camera.focal_point, 
            'view_up': camera.view_up, 
            'clipping_range': camera.clipping_range, 
            'angle': camera.view_angle
          }

    if os.path.exists(filename):
        t = time.asctime(time.gmtime(time.time())).replace(' ', '_').replace(':', '-')
        basename, ext = os.path.splitext(filename)
        if not ext:
            ext = '.json'
        filename = f'{basename}_{t}{ext}'
    with open(filename, 'w') as output:
        json.dump(cam, output)
    print(f'saved camera in {filename}')

def load_camera(filename='camera.json'):
    with open(filename, 'r') as json_file:
        cam = json.load(json_file)
        camera = vtk.vtkCamera(position=cam['position'], 
            focal_point=cam['focal_point'], 
            view_up=cam['view_up'], 
            clipping_range=cam['clipping_range'])
        if 'angle' in cam.keys():
            camera.SetViewAngle(cam['angle'])
        return camera


def print_camera(camera=None, renderer=None):
    if camera is None:
        if renderer is not None:
            camera = renderer.GetActiveCamera()
        else:
            raise ValueError('Missing camera input')
    # ---------------------------------------------------------------
    # Print out the current settings of the camera
    # ---------------------------------------------------------------
    print('Camera settings:')
    print(f' * position:        {camera.position}')
    print(f' * focal point:     {camera.focal_point}')
    print(f' * up vector:       {camera.view_up}')
    print(f' * clipping range:  {camera.clipping_range}')
    print(f' * view angle:      {camera.view_angle}')


def save_light(light=None, renderer=None, filename='light.json'):
    if light is None and renderer is None:
        raise ValueError('No light information provided')
    elif light is None:
        lc = renderer.GetLights()
        it = lc.NewIterator()
        if not it.IsDoneWithTraversal():
            light = it.GetNextItem()

    pos = light.position
    foc = light.focal_point
    angle = light.cone_angle
    cola = light.ambient_color
    cold = light.diffuse_color
    cols = light.specular_color
    intens = light.intensity
    lightdic = { 'position': pos, 'focal_point': foc, 'angle': angle, 'ambient_color': cola,
            'diffuse_color': cold, 'specular_color': cols, 'intensity': intens }
    if os.path.exists(filename):
        t = time.asctime(time.gmtime(time.time())).replace(' ', '_')
        basename, ext = os.path.splitext(filename)
        if not ext:
            ext = '.json'
        filename = f'{basename}_{t}{ext}'
    with open(filename, 'w') as output:
        json.dump(lightdic, output)
    print(f'saved light in {filename}')


def load_one_light(filename):
    with open(filename, 'r') as json_file:
        light_data = json.load(json_file)
        light = vtk.vtkLight(position=light_data['position'], 
            focal_point=light_data['focal_point'], 
            cone_angle=light_data['angle'], 
            ambient_color=light_data['ambient_color'], 
            diffuse_color=light_data['diffuse_color'], 
            specular_color=light_data['specular_color'], 
            intensity=light_data['intensity'])
        light.PositionalOn()
        return light

def load_lights(filename='light.json'):
    collection = vtk.vtkLightCollection()
    if isinstance(filename, list):
        for name in filename:
            collection.AddItem(load_one_light(name))
    else:
        collection.AddItem(load_one_light(filename))
    return collection


def print_light(light):
    print('Light setting:')
    print(f' * position:        {light.position}')
    print(f' * focal point:     {light.focal_point}')
    print(f' * cone angle:      {light.cone_angle}')
    print(f' * ambient color:   {light.ambient_color}')
    print(f' * diffusion color: {light.diffuse_color}')
    print(f' * specular color:  {light.specular_color}')
    print(f' * intensity:       {light.intensity}')
