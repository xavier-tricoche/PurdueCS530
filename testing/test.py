import vtk
import numpy as np
import argparse

import utils.vtk_dataset as vdat
import utils.vtk_rendering as vren

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test utils modules')
    parser.add_argument('id', type=int, help='Test case id:\n 1. Test vtk_dataset\n 2. Test vtk_rendering')
    args = parser.parse_args()

    if args.id == 1:
        vdat.main()
    elif args.id == 2:
        vren.main()

