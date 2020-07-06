'''
 Copyright (c) 2016, UChicago Argonne, LLC
 See LICENSE file.
'''
from rsMap3D.mappers.output.abstactgridwriter import AbstractGridWriter
import numpy as np
import os
try:
    from PIL import Image
except ImportError:
    import Image

STACK_OUTFILE_MERGE_STR = "%s_S%d"

def exportTiffStack(qx, qy, qz, intensity, dim=2, filebase="slice"):
    print (qx.shape)
    print (qy.shape)
    print (qz.shape)
    print (intensity.shape)
    print (filebase)
    if dim==0:
        for ind, val in enumerate(qx):
            im = Image.fromarray(np.squeeze(intensity[ind,:,:]))
            filename = "%s_qx%01dp%01d.tif" % (filebase, val,val*1000)
            im.save(filename)
    if dim==1:
        for ind, val in enumerate(qx):
            im = Image.fromarray(np.squeeze(intensity[:,ind,:]))
            filename = "%s_qy%01dp%01d.tif" % (filebase, val,val*1000)
            im.save(filename)
    if dim==2:
        for ind, val in enumerate(qz):
            im = Image.fromarray(np.squeeze(intensity[:,:,ind]))
            filename = "%s_qz%01dp%01d.tif" % (filebase, val,val*1000)
            im.save(filename)



class ImageStackWriter(AbstractGridWriter):
    FILE_EXTENSION = ""

    def __init__(self):
        super(ImageStackWriter, self).__init__()
        self.index = 0
        
    def getSliceIndex(self):
        return self.index
    
    def setFileInfo(self, fileInfo):
        """
        Set information needed to create the file output.  
        This information is ultimately packed into a tuple
        or list which is used to define a number of parameters.
        [projectName, availableScans, nx, ny, nz (number of points in the 3 dimensions) 
        and the output file name
        """
        if ((fileInfo is None) or (len(fileInfo) == 0)):
            raise ValueError(self.whatFunction() +
                            "passed no filename information " +
                            "requires a tuple with six members:\n"
                            "1. project filename so that a filename can be " +
                            "constructed if filename is blank\n 2. User " +
                            "filename\n" +
                            "3,4,5 - number of pixels for output in " + 
                            "x/y/z directions" +
                            "6 - output file name" + 
                            "7 - outputFileType"+
                            "8 - outputFormat")
        elif (len( fileInfo) != 8):
            raise ValueError(self.whatFunction() +
                            "passed no filename information " +
                            "requires a tuple with six members:\n"
                            "1. project filename so that a filename can be " +
                            "constructed if filename is blank\n 2. User " +
                            "filename\n" +
                            "3,4,5 - number of pixels for output in " + 
                            "x/y/z directions" +
                            "6 - output file name" + 
                            "7 - outputFileType"+
                            "8 - outputFormat")
        self.fileInfo.append(fileInfo[0])
        self.fileInfo.append(fileInfo[1])
        self.nx = fileInfo[2]
        self.ny = fileInfo[3]
        self.nz = fileInfo[4]
        self.outputFileName = fileInfo[5]
        self.outType = fileInfo[6]
        self.outFormat = fileInfo[7]
    
    def setSliceIndex(self, index):
        self.index = index
        
    def write(self):
        print ("Entering ImageStackWriter.write ")
        print (self.qx.shape)
        print (self.qy.shape)
        print (self.qz.shape)
        #dimX = (self.qx[-1] - self.qx[0])/self.nx
        #qxOut = np.linspace(self.qx[0], self.qx[0]+dimX*self.nx, dimX )
        #dimY = (self.qy[-1] - self.qy[0])/self.ny
        #qyOut = np.linspace(self.qy[0], self.qy[0]+dimY*self.ny, dimY )
        #dimZ = (self.qz[-1] - self.qz[0])/self.nz
        #qzOut = np.linspace(self.qz[0], self.qz[0]+dimZ*self.nz, dimZ )   
        dims = (self.nx, self.ny, self.nz)
        arrayData = np.reshape(self.gridData, dims[::-1])
        
        arrayData = np.transpose(arrayData)
        if self.outFormat == "LOG":
            arrayData = np.log(arrayData)
        
        datadir = ""
        filePrefix = ""
        # NEEDS TO BE CHECKED
        if self.outputFileName == "":
            filePrefix = (STACK_OUTFILE_MERGE_STR % 
                               (self.fileInfo[0], \
                                self.fileInfo[1]))
                                #
        else:
            datadir, filename = os.path.split(self.outputFileName)
            filePrefix = os.path.splitext(filename)[0]
            
        exportTiffStack(self.qx, self.qy, self.qz, arrayData, \
                        dim=self.index,\
                        filebase=os.path.join(datadir, filePrefix))
        print ("Exiting ImageStackWriter.write")
            
            
        
        
        