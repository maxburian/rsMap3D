'''
 Copyright (c) 2012, UChicago Argonne, LLC
 See LICENSE file.
'''

import xrayutilities as xu
from rsMap3D.mappers.abstractmapper import AbstractGridMapper
from multiprocessing import Process, Queue
import numpy as np
from scipy.interpolate import griddata
from xrayutilities.exception import InputError
import logging
logger = logging.getLogger(__name__)

def wrapper_interpolate_frame(l_dataslice,q,indx):
    '''
    Interpolation function for gridder.data
    '''
    logger.info("Entering Interpolate Wrapper " + str(indx))
    tempframe = l_dataslice[:,:,0]
    n,m = tempframe.shape
    x,y = np.mgrid[0:n,0:m]
    n_slices =l_dataslice.shape[2]
    for k in range(n_slices):
        tempframe = l_dataslice[:,:,k]
        mask = ~np.isnan(tempframe)
        l_dataslice[:,:,k]=griddata((x[mask], y[mask]), tempframe[mask], (x, y), method='linear')
    logger.info("Interpolate Wrapper " + str(indx)+" is done!")
    q.put(l_dataslice)


class QGridMapper(AbstractGridMapper):
    '''
    Override parent class to add in output type
    '''
    def __init__(self, dataSource, \
                 outputFileName, \
                 outputType, \
                 nx=200, ny=201, nz=202, \
                 transform = None, \
                 gridWriter = None, **kwargs):
        super(QGridMapper, self).__init__(dataSource, \
                 outputFileName, \
                 nx=nx, ny=ny, nz=nz, \
                 transform = transform, \
                 gridWriter = gridWriter, \
                 **kwargs)
        self.outputType = outputType
        
    def getFileInfo(self):
        '''
        Override parent class to add in output type
        '''
        return (self.dataSource.projectName, 
                self.dataSource.availableScans[0],
                self.nx, self.ny, self.nz,
                self.outputFileName,
                self.outputType,
                self.outFormat)
    
    '''
    This map provides an x, y, z grid of the data.
    '''
    #@profile
    def processMap(self, **kwargs):
        """
        read ad frames and grid them in reciprocal space
        angular coordinates are taken from the spec file
    
        **kwargs are passed to the rawmap function
        """
        maxImageMem = self.appConfig.getMaxImageMemory()
        gridder = xu.FuzzyGridder3D(self.nx, self.ny, self.nz)
        gridder.KeepData(True)
        rangeBounds = self.dataSource.getRangeBounds()
        logger.debug(rangeBounds)
        try:
            # repository version or xrayutilities > 1.0.6
            gridder.dataRange(rangeBounds[0], rangeBounds[1], 
                              rangeBounds[2], rangeBounds[3], 
                              rangeBounds[4], rangeBounds[5], 
                              True)
        except:
            # xrayutilities 1.0.6 and below
            gridder.dataRange((rangeBounds[0], rangeBounds[1]), 
                              (rangeBounds[2], rangeBounds[3]), 
                              (rangeBounds[4], rangeBounds[5]), 
                              True)
                              
        imageToBeUsed = self.dataSource.getImageToBeUsed()
        progress = 0
        for scan in self.dataSource.getAvailableScans():

            if True in imageToBeUsed[scan]:
                imageSize = self.dataSource.getDetectorDimensions()[0] * \
                            self.dataSource.getDetectorDimensions()[1]
                numImages = len(imageToBeUsed[scan])
                if imageSize*4*numImages <= maxImageMem:
                    kwargs['mask'] = imageToBeUsed[scan]
                    qx, qy, qz, intensity = self.dataSource.rawmap((scan,), **kwargs)
                    # convert data to rectangular grid in reciprocal space
                    try:
                        gridder(qx, qy, qz, intensity)
                        progress += 50
                        if self.progressUpdater is not None:
                            self.progressUpdater(progress)
                    except InputError as ex:
                        print ("Wrong Input to gridder")
                        print ("qx Size: " + str( qx.shape))
                        print ("qy Size: " + str( qy.shape))
                        print ("qz Size: " + str( qz.shape))
                        print ("intensity Size: " + str(intensity.shape))
                        raise InputError(ex)
                else:
                    nPasses = int(imageSize*4*numImages/ maxImageMem + 1)
                    
                    for thisPass in range(nPasses):
                        imageToBeUsedInPass = np.array(imageToBeUsed[scan])
                        imageToBeUsedInPass[:int(thisPass*numImages/nPasses)] = False
                        imageToBeUsedInPass[int((thisPass+1)*numImages/nPasses):] = False
                        
                        if True in imageToBeUsedInPass:
                            kwargs['mask'] = imageToBeUsedInPass
                            qx, qy, qz, intensity = \
                                self.dataSource.rawmap((scan,), **kwargs)
                            # convert data to rectangular grid in reciprocal space
                            try:
                                gridder(qx, qy, qz, intensity)
                        
                                progress += 1.0/nPasses* 50.0
                                if self.progressUpdater is not None:
                                    self.progressUpdater(progress)
                            except InputError as ex:
                                print ("Wrong Input to gridder")
                                print ("qx Size: " + str( qx.shape))
                                print ("qy Size: " + str( qy.shape))
                                print ("qz Size: " + str( qz.shape))
                                print ("intensity Size: " + str(intensity.shape))
                                raise InputError(ex)
                        else:
                            progress += 1.0/nPasses* 50.0
                            if self.progressUpdater is not None:
                                self.progressUpdater(progress)
            progress=50.0
            self.progressUpdater(progress)
            
            
            #Interpolating zero values
            data = gridder.data.copy()
            
            #First, set all zeros to NANs
            data[data ==0]=np.nan
            
            #Setting some parameters
            nprocs = 4
            n_slices =data.shape[2]
            jump = int(n_slices/nprocs)
            
            #Init multiprocessing variables
            queue, process, index = [], [], []
            
            logger.info('Starting Interpolation using ' +str(nprocs)+' CPUs')
            
            for i in range(nprocs):
                queue.append(Queue())
                if i == (nprocs-1):
                    finalidx = n_slices
                else:
                   finalidx = (i + 1) * jump
                dataslice = data[:,:,(i*jump):finalidx]
                logger.debug('Starting process: '+str(i)+ ' for slices ' +str(i*jump)+ ' to '+str(finalidx))
                process.append(Process(target=wrapper_interpolate_frame, args=(dataslice, queue[-1],i,)))
                process[-1].start()
                index.append(i)
                
            logger.debug('All processes started!')
            
            for q, p,i in zip(queue, process,index):
                if i == (nprocs-1):
                    finalidx = n_slices
                else:
                   finalidx = (i + 1) * jump
                logger.debug('Getting Data from proccess: '+str(i)+ ' for slices ' +str(i*jump)+ ' to '+str(finalidx))
                data[:,:,(i*jump):finalidx]=q.get()
                p.join()
                progress += 1.0/nprocs * 50.0
                if self.progressUpdater is not None:
                    self.progressUpdater(progress)

            self.progressUpdater(100.0)
            
        return gridder.xaxis,gridder.yaxis,gridder.zaxis,data,gridder
    
    
