'''
 Copyright (c) 2014, UChicago Argonne, LLC
 See LICENSE file.
'''
from rsMap3D.exception.rsmap3dexception import DetectorConfigException,\
    RSMap3DException
from rsMap3D.datasource.Sector33SpecDataSource import LoadCanceledException
from rsMap3D.gui.rsm3dcommonstrings import CANCEL_STR
import h5py
from rsMap3D.datasource.abstractDataSource import AbstractDataSource
from rsMap3D.config.rsmap3dconfig import RSMap3DConfig
from rsMap3D.datasource.DetectorGeometry.detectorgeometryforescan \
    import DetectorGeometryForEScan
import math
import numpy as np
import glob
import os
import string

H5_INCIDENT_ENERGY = '/entry1/sample/incident_energy'
H5_ROI_START_X = '/entry1/detector/startx'
H5_ROI_START_Y = '/entry1/detector/starty'
H5_ROI_END_X = '/entry1/detector/endx'
H5_ROI_END_Y = '/entry1/detector/endy'
H5_IMAGE = '/entry1/data/data'

class Sector34NexusEscanSource(AbstractDataSource):
    '''
    '''
    
    def __init__(self, \
                 projectDir, \
                 projectName, \
                 projectExtension,
                 detConfigFile,
                 detectorId="PE1621 723-3335",
                 **kwargs):
        '''
        '''
        super(Sector34NexusEscanSource, self).__init__()
        self.projectDir = str(projectDir)
        self.projectName = str(projectName)
        self.projectExtension = str(projectExtension)
        self.detConfigFile = str(detConfigFile)
        self.detectorId = detectorId
        self.files = None
        self.availableFiles = []
        self.detectorROI = []
        self.incidentEnergy = {}
        self.progressUpdater = None
        self.progress = 0
        self.progressInc = 1.0 *100.0
        self.progressMax = 1
        self.cancelLoad = False
        
        

    def findImageQs(self):
        rsMap3DCongfig = RSMap3DConfig()
        maxImageMem = rsMap3DCongfig.getMaxImageMemory()
        imageSize = self.getDetectorDimensions()[0] * \
                self.getDetectorDimensions()[1]
        
        numImages = len(self.availableFiles)
        if imageSize *4 * numImages <=maxImageMem:
            (qx,qy, qz) = self.qsForDetector()
            idx = range(len(qx))
            xmin = [np.min(qx[i]) for i in idx]
            xmax = [np.max(qx[i]) for i in idx]
            ymin = [np.min(qy[i]) for i in idx]
            ymax = [np.max(qy[i]) for i in idx]
            zmin = [np.min(qz[i]) for i in idx]
            zmax = [np.max(qz[i]) for i in idx]
        else:
            xmin = []
            xmax = []
            ymin = []
            ymax = []
            zmin = []
            zmax = []
            nPasses = imageSize * 4 *numImages/maxImageMem
            for thisPass in range(nPasses):
                firstImage = thisPass *numImages/nPasses
                lastImage = (thisPass+1)* numImages/nPasses;
                (qx,qy,qz) = self.qsForDetector(startFile = firstImage, 
                                                endFile = lastImage)
                idx = range(len(qx))
                [xmin.append(np.min(qx[i])) for i in idx]
                [xmax.append(np.max(qx[i])) for i in idx]
                [ymin.append(np.min(qy[i])) for i in idx]
                [ymax.append(np.max(qy[i])) for i in idx]
                [zmin.append(np.min(qz[i])) for i in idx]
                [zmax.append(np.max(qz[i])) for i in idx]
            
        return (xmin, xmax, ymin, ymax, zmin, zmax)
                     
    def findScanQs(self, xmin, xmax, ymin, ymax, zmin, zmax):
        '''
        find the overall boundaries for a scan given the min/max boundaries
        of each image in the scan
        '''
        scanXmin = np.min( xmin)
        scanXmax = np.max( xmax)
        scanYmin = np.min( ymin)
        scanYmax = np.max(  ymax)
        scanZmin = np.min(  zmin)
        scanZmax = np.max(  zmax)
        return scanXmin, scanXmax, scanYmin, scanYmax, scanZmin, scanZmax

    def getImageToBeUsed(self):
        '''
        Return a dictionary containing list of images to be used in each scan.
        '''
        return self.imageToBeUsed
     
    def getReferenceNames(self):
        names = []
        names.append("Energy (keV)")
        return names
    
    def getReferenceValues(self, scan):
        
        values = []
        for energy in self.incidentEnergy.values():
            values.append([energy,]) 
        return values

    def loadDetectorConfig(self):
        try:
            self.detConfig = DetectorGeometryForEScan(self.detConfigFile)
            self.detector = self.detConfig.getDetectorById(self.detectorId)
            self.detectorDimensions = \
                self.detConfig.getNpixels(self.detector)
            self.detectorSize = self.detConfig.getSize(self.detector)
            self.detectorPixelWidth = \
                [self.detectorSize[0]/self.detectorDimensions[0],\
                 self.detectorSize[1]/self.detectorDimensions[1]]
            self.detectorRotation = self.detConfig.getRotation(self.detector)   
            self.detectorTranslation = \
                self.detConfig.getTranslation(self.detector)  
            Rx = self.detectorRotation[0]
            Ry = self.detectorRotation[1]
            Rz = self.detectorRotation[2]    
            theta = math.sqrt(Rx*Rx+Ry*Ry+Rz*Rz) 
            
            if theta == 0:
                self.rho = np.array[[1,0,0],[0,1,0],[001]]
            else:
                c = math.cos(theta)
                s = math.sin(theta)
                c1 = 1 - c
                Rx /= theta      # normalize to unit vector
                Ry /= theta
                Rz /= theta 
                
                self.rho = \
                    np.array([[c + Rx*Rx*c1, Rx*Ry*c1 - Rz*s, Ry*s + Rx*Rz*c1],\
                              [Rz*s + Rx*Ry*c1, c + Ry*Ry*c1, -Rx*s + Ry*Rz*c1],\
                              [-Ry*s + Rx*Rz*c1,Rx*s + Ry*Rz*c1, c + Rz*Rz*c1]])
                self.rho2 = \
                    np.array([[c + Rx*Rx*c1, Rz*s + Rx*Ry*c1, Ry*s + Rx*Rz*c1],\
                              [Rx*Ry*c1 - Rz*s, c + Ry*Ry*c1,  Rx*s + Ry*Rz*c1],\
                              [Ry*s + Rx*Rz*c1,-Rx*s + Ry*Rz*c1, c + Rz*Rz*c1]])
                
        except DetectorConfigException as ex:
            print ("--Error Reading detectorConfig")
            raise ex
        except Exception as ex:
            print ("---Unhandled Exception in loading detector config")
            raise ex
        
    def loadSource(self):
        self.loadDetectorConfig()
        
        if self.files == None:
            print("Getting file list")
            fileFilter = str(os.path.join(self.projectDir, string.rsplit(self.projectName, '_',1)[0])) + \
                         "_[0-9]*" + \
                         self.projectExtension
                         
            fileList = glob.glob(fileFilter)
            print("Done Getting File List")
        if fileList == []:
                raise RSMap3DException("No files Found matching " + fileFilter)
        self.files = range(1,len(fileList)+1)

        if self.progressUpdater <> None:
            self.progressMax = len(self.files) *100.0
            self.progressUpdater(self.progress, self.progressMax)

        for afile in self.files:
            if (self.cancelLoad):
                self.cancelLoad = False
                raise LoadCanceledException(CANCEL_STR)
            else:
                filename = os.path.join(self.projectDir, \
                               string.rsplit(self.projectName, '_', 1)[0]) + \
                               '_' + \
                               str(afile) + \
                               self.projectExtension
                #print filename
                if os.path.exists(filename):
                    #curScan = self.sd[afile]
                    self.availableFiles.append(afile)
                    try:
                        hdfFile = h5py.File(filename, "r")
                        self.incidentEnergy[afile] = \
                            hdfFile[H5_INCIDENT_ENERGY].value[0]
                        self.detectorROI = \
                            [hdfFile[H5_ROI_START_X].value[0], \
                             hdfFile[H5_ROI_END_X].value[0], \
                             hdfFile[H5_ROI_START_Y].value[0], \
                             hdfFile[H5_ROI_END_Y].value[0]]
                        hdfFile.close()
                    except Exception:
                        print "Trouble Opening File" + filename
                if self.progressUpdater <> None:
                    self.progressUpdater(self.progress, self.progressMax)
                    self.progress += self.progressInc
            if afile == 1:
                print("Starting to get Energy independant Information")
                xIndexArray = range(self.detectorROI[0], self.detectorROI[1] +1)
                yIndexArray = range(self.detectorROI[2], self.detectorROI[3] +1)

                indexMesh = np.meshgrid(xIndexArray, yIndexArray)
                qpxyz = self.pixel2q_2(indexMesh, None)
                self.qpx, self.qpy, self.qpz = qpxyz[:,:,0], qpxyz[:,:,1], qpxyz[:,:,2]
                print "self.qpx"
                print self.qpx
                print "self.qpy"
                print self.qpy
                print "self.qpz"
                print self.qpz                      
                print("Ending Energy independant Information")

        #reset progress bar for second pass
        if self.progressUpdater <> None:
            self.progress = 0.0
            self.progressUpdater(self.progress, self.progressMax)

        self.imageBounds[1] = self.findImageQs()
        self.availableScans.append(1)
            
    def pixel2XYZ(self, pixelX, pixelY):
        
        xp = (pixelX - 0.5*(self.detectorDimensions[0])-1) * \
            self.detectorPixelWidth[0]
        yp = (pixelY - 0.5*(self.detectorDimensions[1])-1) * \
            self.detectorPixelWidth[1]
            
        xp += self.detectorTranslation[0]
        yp += self.detectorTranslation[1]
        zp = self.detectorTranslation[2]
        if(pixelX == 1 and pixelY == 1):
            print "xp,yp,zp"
            print xp,yp,zp
        xyz = [(self.rho[0][0]*xp + self.rho[0][1]*yp + self.rho[0][2]*zp), \
               (self.rho[1][0]*xp + self.rho[1][1]*yp + self.rho[1][2]*zp), \
               (self.rho[2][0]*xp + self.rho[2][1]*yp + self.rho[2][2]*zp)]
        return xyz

    def pixel2XYZ_2(self, indexMesh):
            xp = np.subtract(indexMesh[0], 0.5*self.detectorDimensions[0])
            xp = np.subtract(xp, 1.0)
            xp = np.multiply(xp, self.detectorPixelWidth[0])
            xp = np.add(xp, self.detectorTranslation[0])

            yp = np.subtract(indexMesh[1], 0.5*self.detectorDimensions[1])
            yp = np.subtract(yp, 1.0)
            yp = np.multiply(yp, self.detectorPixelWidth[1])
            yp = np.add(yp, self.detectorTranslation[1])
            
            zp = np.multiply(np.ones((self.detectorDimensions[0], self.detectorDimensions[1])), 
                             self.detectorTranslation[2])
            print "xp[0][0], yp[0][0], zp[0][0]"
            print xp[0][0], yp[0][0], zp[0][0]
            xpp = np.inner(self.rho[0,:], np.stack((xp, yp, zp), axis=-1))
            ypp = np.inner(self.rho[1,:], np.stack((xp, yp, zp), axis=-1))
            zpp = np.inner(self.rho[2,:], np.stack((xp, yp, zp), axis=-1))
            xyz = np.stack((xpp, ypp, zpp), axis=-1)
            
            print "shape x,y,z" + str(xyz.shape)
            return xyz
    
    def pixel2q(self, pixelX, pixelY, qhat, depth=0):
        ki = [0, 0, 1]
        
        kout = self.pixel2XYZ(pixelX, pixelY)
        
        if depth != 0:
            kout -= depth*ki
        koutnorm = np.linalg.norm(kout)
        if koutnorm != 0:
            kout /= koutnorm 
        
        qhat = kout-ki
        return qhat
    
    def pixel2q_2(self, indexMesh, qhat, depth=0):
        ki = [0, 0, 1]
        
        kout = self.pixel2XYZ_2(indexMesh)
        
        if depth != 0:
            kout = np.subtract(kout, depth*ki)
        koutnorm = np.linalg.norm(kout, axis=2)
        print "koutnorm"
        print koutnorm
        print koutnorm.shape
        print kout.shape
        if np.any(koutnorm):
            for index in range(np.ma.size(kout, 2)):
                print "index " + str(index)
                kout[:,:,index] = np.divide(kout[:,:,index], koutnorm) 
        
        qhat = np.subtract(kout,ki)
        return qhat
    
    def qsForDetector(self, startFile=0, endFile=0):     
        #if startFile and endFile are nonzero and Valid
        #then give qs only between speicified file else
        # if both zero give for all, if not vaild, throw
        # an exception
        if((startFile == 0) and (endFile == 0) ) :
            processFiles = self.availableFiles
        elif ((startFile >=0) and (startFile <= len(self.availableFiles))) and \
               ((endFile >=0) and (endFile <= len(self.availableFiles))) and \
                (startFile <= endFile):
            processFiles = self.availableFiles[startFile:endFile]
        else: 
            raise ValueError("startFile and EndFile must be valid file " +
                             "indexes. StartFile = " + str(startFile) + 
                             "endFile = " + str(endFile))
        xIndexArray =  range(self.detectorROI[0], self.detectorROI[1]+1)
        yIndexArray =  range(self.detectorROI[2], self.detectorROI[3]+1)
        numFiles = len(processFiles)
        sizeXArray = len(xIndexArray)
        sizeYArray = len(yIndexArray)
        arrSize = [numFiles, sizeXArray, sizeYArray]
#         qx = np.zeros(arrSize)
#         qy = np.zeros(arrSize)
#         qz = np.zeros(arrSize)
#         qx = []
#         qy = []
#         qz = []
        twoPiOverLambda = []
        arrSize = [len(yIndexArray), \
                       len(xIndexArray)]
        for afile in processFiles:
            if self.progressUpdater <> None:
                self.progressUpdater(self.progress, self.progressMax)
            self.progress += self.progressInc 
            twoPiOverLambda.append(2*np.pi * self.incidentEnergy[afile] / 1.23985)
            
#             qx[afile-processFiles[0],:,:] = np.multiply(self.qpx, twoPiOverLamda) 
#             qy[afile-processFiles[0],:,:] = np.multiply(self.qpy, twoPiOverLamda) 
#             qz[afile-processFiles[0],:,:] = np.multiply(self.qpz, twoPiOverLamda) 
#             qx.append(np.multiply(self.qpx, twoPiOverLamda)) 
#             qy.append(np.multiply(self.qpy, twoPiOverLamda)) 
#             qz.append(np.multiply(self.qpz, twoPiOverLamda)) 
        qx = np.multiply.outer(twoPiOverLambda, self.qpx)
        print "qx.shape"
        print qx.shape
        qy = np.multiply.outer(twoPiOverLambda, self.qpy)
        qz = np.multiply.outer(twoPiOverLambda, self.qpz)
        return qx, qy, qz

    def rawmap(self,scans, angdelta=[0,0,0,0,0],
            adframes=None, mask = None):

        if mask == None:
            maskWasNone = True
        else:
            maskWasNone = False
        
        if maskWasNone == True:
            firstScan = 0
            lastScan = 0
        else:
            a = np.array(mask)
            trueLoc = np.argwhere(a)
            firstScan = trueLoc[0]
            lastScan = trueLoc[-1]
        qx, qy, qz = self.qsForDetector(startFile=firstScan, endFile=lastScan)
        intensity = np.array([])
        arrayInitializedForScan = False
        offset=0
        foundIndex = 0
        self.availableFiles.sort()
        for afile in self.availableFiles[firstScan:lastScan]:
            if mask[afile - 1]:
                filename = os.path.join(self.projectDir, \
                               string.rsplit(self.projectName, '_', 1)[0]) + \
                               '_' + \
                               str(afile) + \
                               self.projectExtension
                hdfFile = h5py.File(filename, "r")
                img = \
                    hdfFile[H5_IMAGE].value
                if not arrayInitializedForScan:
                    if not intensity.shape[0]:
                        intensity = np.zeros((len(self.availableFiles[firstScan:lastScan]),) + img.shape)
                        arrayInitializedForScan = True
                    else: 
                        offset = intensity.shape[0]
                        intensity = np.concatenate(
                            (intensity,
                            (np.zeros((np.count_nonzero(len(self.availableFiles[firstScan:lastScan])),) + img.shape))),
                            axis=0)
                        arrayInitializedForScan = True
                intensity[foundIndex+offset,:,:] = img
                foundIndex += 1
                
                hdfFile.close()
        return qx, qy, qz, intensity
