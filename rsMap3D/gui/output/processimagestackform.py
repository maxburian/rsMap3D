'''
 Copyright (c) 2016, UChicago Argonne, LLC
 See LICENSE file.
'''
import logging
import PyQt5.QtGui as qtGui
import PyQt5.QtCore as qtCore
import PyQt5.QtWidgets as qtWidgets

from  PyQt5.QtCore import pyqtSlot as Slot

from rsMap3D.gui.output.abstractgridoutputform import AbstractGridOutputForm
from rsMap3D.gui.rsm3dcommonstrings import BROWSE_STR, SAVE_DIR_STR, WARNING_STR,\
    BINARY_OUTPUT
import os
from rsMap3D.mappers.gridmapper import QGridMapper
from rsMap3D.mappers.output.imagestackwriter import ImageStackWriter
logger = logging.getLogger(__name__)

class ProcessImageStackForm(AbstractGridOutputForm):
    '''
    Process grid data and output a stack of TIFF images.
    '''
    FORM_TITLE = "Image Stack Output"
    LIN_RADIO_NAME = "Linear"
    LOG_RADIO_NAME = "Logarithmic"
    
    @staticmethod
    def createInstance(parent=None, appConfig=None):
        '''
        A static method to create an instance of this class.  The UI selects which processor method to use 
        from a menu so this method allows creating an instance without knowing what to create ahead of time. 
        '''
        return ProcessImageStackForm(parent=parent, appConfig=appConfig)

    def __init__(self, **kwargs):
        '''
        Constructor.  Typically instances should be created by createInstance method.
        '''
        super(ProcessImageStackForm, self).__init__(**kwargs)
        self.gridWriter = ImageStackWriter()
        layout = qtWidgets.QVBoxLayout()
        self.dataBox = self._createDataBox()
        controlBox = self._createControlBox()
        
        layout.addWidget(self.dataBox)
        layout.addWidget(controlBox)
        self.setLayout(layout)
        self.linRadio.setChecked(True)
        self.outputType = BINARY_OUTPUT
        
    @Slot()
    def _browseForOutputDirectory(self):
        '''
        Launch file browser to find location to write image files.
        '''
        if self.outputDirTxt.text() == "":
            dirName = str(qtWidgets.QFileDialog.getExistingDirectory(None, 
                                                              SAVE_DIR_STR))
        else:
            curName = str(self.outputDirTxt.text())
            dirName = str(qtWidgets.QFileDialog.getExistingDirectory(None, 
                                                              SAVE_DIR_STR,
                                                              directory = curName))
            
        logger.debug("dirname: " + dirName)
        logger.debug("os.path.dirname(str(dirName): "+os.path.dirname(str(dirName)))
        
        if dirName != "":
            if os.path.exists(str(dirName)):
                self.outputDirTxt.setText(dirName)
                self.outputDirName = dirName
                self.outputDirTxt.editingFinished.emit()
            else:
                message = qtWidgets.QMessageBox()
                message.warning(self, 
                                WARNING_STR, 
                                "The specified directory does not exist")
                self.outputDirTxt.setText(dirName)
                self.outputDirName = dirName
                self.outputDirTxt.editingFinished.emit()
            if not os.access(dirName, os.W_OK):
                message = qtWidgets.QMessageBox()
                message.warning(self,
                                WARNING_STR,
                                "The specified directory is not writable")
                
    def _createDataBox(self):
        dataBox = super(ProcessImageStackForm, self)._createDataBox()
        layout = dataBox.layout()
        
        row = layout.rowCount()
        row += 1

        label = qtWidgets.QLabel("Output Directory")
        layout.addWidget(label, row,0)
        self.outputDirName = ""
        self.outputDirTxt = qtWidgets.QLineEdit()
        self.outputDirTxt.setText(self.outputDirName)
        layout.addWidget(self.outputDirTxt, row,1)
        self.outputDirButton = qtWidgets.QPushButton(BROWSE_STR)
        layout.addWidget(self.outputDirButton, row, 2)

        row += 1
        label = qtWidgets.QLabel("Image File Prefix")
        layout.addWidget(label, row, 0)
        self.imageFilePrefix = ""
        self.imageFilePrefixTxt = qtWidgets.QLineEdit()
        self.imageFilePrefixTxt.setText(self.imageFilePrefix)
        layout.addWidget(self.imageFilePrefixTxt, row,1)
        
        row += 1
        label = qtWidgets.QLabel("Output Format")
        layout.addWidget(label, row,0)
        subdataLayout = qtWidgets.QHBoxLayout()
        layout.addLayout(subdataLayout, row,1)
        self.outFormatGroup = qtWidgets.QButtonGroup(self)
        self.linRadio = qtWidgets.QRadioButton(self.LIN_RADIO_NAME)
        self.logRadio = qtWidgets.QRadioButton(self.LOG_RADIO_NAME)
        self.outFormatGroup.addButton(self.linRadio, 1)
        self.outFormatGroup.addButton(self.logRadio, 2)
        subdataLayout.addWidget(self.linRadio)
        subdataLayout.addWidget(self.logRadio)
        
        
        row += 1
        label = qtWidgets.QLabel("Slice Axis")
        layout.addWidget(label, row, 0)
        self.axisChoices = ["0", "1", "2"]
        self.axisSelector = qtWidgets.QComboBox()
        self.axisSelector.addItems(self.axisChoices)
        self.axisSelector.setCurrentIndex(self.gridWriter.getSliceIndex())
        layout.addWidget(self.axisSelector)
        
        #Connect signals for this class        
        self.outputDirButton.clicked.connect(self._browseForOutputDirectory)
#         self.connect(self.outputDirButton, \
#                      qtCore.SIGNAL(EDIT_FINISHED_SIGNAL), 
#                      self._editFinishedOutputDir)
        self.outputDirTxt.editingFinished.connect(self._editFinishedOutputDir)
        self.setFileName[str].connect(self.setOutDirTxt)
        self.imageFilePrefixTxt.editingFinished.connect(
            self._editFinishedOutputDir)
        self.axisSelector.currentIndexChanged[int].connect(self.updateSliceAxis)

        
        return dataBox
    
    @Slot()
    def _editFinishedOutputDir(self):
        '''
        Process output directory name as inputs are completed.
        '''
        dirName = str(self.outputDirTxt.text())
        imageFilePrefix = str(self.imageFilePrefixTxt.text())
        logger.debug((os.path.dirname(dirName)))
        #"process directory"
        if dirName != "":
            if os.path.exists(os.path.dirname(dirName)):    #use specified dir if it exists
                self.outputDirName = dirName
            else:                          #use current path
                if dirName == "":
                    dirName = os.path.realpath(os.path.curdir)
                else:
                    message = qtWidgets.QMessageBox()
                    message.warning(self,
                                    WARNING_STR,
                                    "The specified directory \n" +
                                    str(dirName) + 
                                    "\ndoes not exist")
        
        #"process file prefix"
        if imageFilePrefix != "":
            for badChar in ['\\', '/', ':', '*', '?', '<', '>', '|']:
                if badChar in imageFilePrefix:
                    message = qtWidgets.QMessageBox()
                    message.warning(self,
                                    WARNING_STR,
                                    "The specified imagePrefix conatins one " +
                                    "of the following invalid characters \/:*?<>|")
            else:
                self.imageFilePrefix = imageFilePrefix
                
    def getOutputFileName(self):
        '''
        Override from base class.  In this case return a join of two of the inputs.  This is used to 
        provide info during runMapper method.
        '''
        logger.debug(os.path.join(self.outputDirName, self.imageFilePrefix))
        return os.path.join(self.outputDirName, self.imageFilePrefix)
    
                
    @Slot(int)
    def updateSliceAxis(self, index):
        '''
        record changes as the axis for slicing is changed
        '''
        self.gridWriter.setSliceIndex(index)
        
    def runMapper(self, dataSource, transform):
        '''
        Run the selected mapper.  Writer specific class should be specified
        in the application specific subclass.  A list of forms is provided in 
        dataSource classes.
        '''
        logger.debug ("Entering " + self.FORM_TITLE + " " + \
            str(self.gridWriter))
        self.dataSource = dataSource
        nx = int(self.xDimTxt.text())
        ny = int(self.yDimTxt.text())
        nz = int(self.zDimTxt.text())
        self.outputFileName = self.getOutputFileName()
        if self.linRadio.isChecked():
            self.outFormat = "LIN"
        else:
            self.outFormat = "LOG"
            
        # NEEDS TO BE CHECKED    
        if self.outputFileName == "":
            self.outputFileName = os.path.join(dataSource.projectDir,  \
                "%s%s" %(dataSource.projectName,self.gridWriter.FILE_EXTENSION) )
            self.setFileName.emit(self.outputFileName)
        if os.access(os.path.dirname(self.outputDirName), os.W_OK):
            self.mapper = QGridMapper(dataSource, \
                                     self.outputFileName, \
                                     self.outputType,\
                                     nx=nx, ny=ny, nz=nz,
                                     transform = transform,
                                     gridWriter = self.gridWriter,
                                     appConfig=self.appConfig,\
                                     outFormat = self.outFormat)
            self.mapper.setProgressUpdater(self._updateProgress)
            self.mapper.doMap()
        else:
            self.processError.emit("The specified directory \n" + \
                                   str(os.path.dirname(self.outputFileName)) + \
                                   "\nis not writable")
        logger.debug ("Exit " + self.FORM_TITLE)
        
    @Slot(str)
    def setOutDirTxt(self, outFile):
        logger.debug(METHOD_ENTER_STR)
        self.outputDirTxt.setText(outFile)
        self.outputDirTxt.editingFinished.emit()