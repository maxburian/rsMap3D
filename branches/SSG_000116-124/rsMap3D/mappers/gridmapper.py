'''
 Copyright (c) 2012, UChicago Argonne, LLC
 See LICENSE file.
'''

import xrayutilities as xu
from rsMap3D.mappers.abstractmapper import AbstractGridMapper

class QGridMapper(AbstractGridMapper):
    '''
    This map provides an x, y, z grid of the data.
    '''

    def processMap(self, **kwargs):
        """
        read ad frames and grid them in reciprocal space
        angular coordinates are taken from the spec file
    
        **kwargs are passed to the rawmap function
        """
    
        gridder = xu.Gridder3D(self.nx, self.ny, self.nz)
        gridder.KeepData(True)
        rangeBounds = self.dataSource.getRangeBounds()
        gridder.dataRange((rangeBounds[0], rangeBounds[1]), 
                          (rangeBounds[2], rangeBounds[3]), 
                          (rangeBounds[4], rangeBounds[5]), 
                          True)
        
        imageToBeUsed = self.dataSource.getImageToBeUsed()
        progress = 1
        for scan in self.dataSource.getAvailableScans():

            if True in imageToBeUsed[scan]:
                qx, qy, qz, intensity = self.rawmap((scan,), **kwargs)
                
                # convert data to rectangular grid in reciprocal space
                gridder(qx, qy, qz, intensity)
            if self.progressUpdater <> None:
                self.progressUpdater(progress)
            progress += 1
            
        return gridder.xaxis,gridder.yaxis,gridder.zaxis,gridder.data,gridder