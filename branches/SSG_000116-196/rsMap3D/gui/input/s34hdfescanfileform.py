'''
 Copyright (c) 2014, UChicago Argonne, LLC
 See LICENSE file.
'''
import PyQt4.QtGui as qtGui
import PyQt4.QtCore as qtCore
from rsMap3D.gui.input.abstractimageperfileview import AbstractImagePerFileView
from rsMap3D.gui.rsm3dcommonstrings import BROWSE_STR, EMPTY_STR,\
     SELECT_DETECTOR_CONFIG_TITLE, DETECTOR_CONFIG_FILE_FILTER, WARNING_STR,\
    SELECT_HDF_FILE_TITLE, HDF_FILE_FILTER
from rsMap3D.gui.qtsignalstrings import CLICKED_SIGNAL, EDIT_FINISHED_SIGNAL,\
    CURRENT_INDEX_CHANGED_SIGNAL
import os.path

class S34HDFEScanFileForm(AbstractImagePerFileView):
    '''
    classdocs
    '''


    def __init__(self, parent=None):
        '''
        Constructor
        '''
        super(S34HDFEScanFileForm, self).__init__()

        self.fileDialogTitle = SELECT_HDF_FILE_TITLE
        self.fileDialogFilter = HDF_FILE_FILTER

        self.dataBox = self._createDataBox()
        controlBox = self._createControlBox()
        
        self.layout.addWidget(self.dataBox)
        self.layout.addWidget(controlBox)
        self.setLayout(self.layout);

    def _browseForDetFile(self):
        '''
        Launch file selection dialog for Detector file.
        '''
        if self.detConfigTxt.text() == EMPTY_STR:
            fileName = qtGui.QFileDialog.getOpenFileName(None, \
                                            SELECT_DETECTOR_CONFIG_TITLE, \
                                            filter=DETECTOR_CONFIG_FILE_FILTER)
        else:
            fileDirectory = os.path.dirname(str(self.detConfigTxt.text()))
            fileName = qtGui.QFileDialog.getOpenFileName(None, \
                                         SELECT_DETECTOR_CONFIG_TITLE, \
                                         filter=DETECTOR_CONFIG_FILE_FILTER, \
                                         directory = fileDirectory)
        if fileName != EMPTY_STR:
            self.detConfigTxt.setText(fileName)
            self.detConfigTxt.emit(qtCore.SIGNAL(EDIT_FINISHED_SIGNAL))

    def checkOkToLoad(self):
        '''
        Make sure we have valid file names for project, instrument config, 
        and the detector config.  If we do enable load button.  If not disable
        the load button
        '''
        projFileOK = AbstractImagePerFileView.checkOkToLoad(self)
        if projFileOK and \
            os.path.isfile(self.detConfigTxt.text()):
            retVal = True
            self.loadButton.setEnabled(retVal)
        else:
            retVal = False
            self.loadButton.setDisabled(not retVal)
        return retVal
    
    def _createDataBox(self):
        '''
        Create widgets for collecting data
        '''
        super(S34HDFEScanFileForm, self)._createDataBox()
        dataBox = super(S34HDFEScanFileForm, self)._createDataBox()
        dataLayout = dataBox.layout()
        row = dataLayout.rowCount()

        row += 1
        label = qtGui.QLabel("Detector Config File:");
        self.detConfigTxt = qtGui.QLineEdit()
        self.detConfigFileButton = qtGui.QPushButton(BROWSE_STR)
        dataLayout.addWidget(label, row, 0)
        dataLayout.addWidget(self.detConfigTxt, row, 1)
        dataLayout.addWidget(self.detConfigFileButton, row, 2)

        row += 1
        label = qtGui.QLabel("Output Type")
        self.outTypeChooser = qtGui.QComboBox()
        self.outTypeChooser.addItem(self.SIMPLE_GRID_MAP_STR)
        #self.outTypeChooser.addItem(self.POLE_MAP_STR)
        dataLayout.addWidget(label, row, 0)
        dataLayout.addWidget(self.outTypeChooser, row, 1)

        dataBox.setLayout(dataLayout)
        
        # Add Signals between widgets
        self.connect(self.detConfigFileButton, \
                     qtCore.SIGNAL(CLICKED_SIGNAL), \
                     self._browseForDetFile)
        self.connect(self.detConfigTxt, \
                     qtCore.SIGNAL(EDIT_FINISHED_SIGNAL), \
                     self._detConfigChanged)
        self.connect(self.outTypeChooser, \
                     qtCore.SIGNAL(CURRENT_INDEX_CHANGED_SIGNAL), \
                     self._outputTypeChanged)
        
        return dataBox

    def _detConfigChanged(self):
        '''
        '''
        if os.path.isfile(self.detConfigTxt.text()) or \
           self.detConfigTxt.text() == "":
            self.checkOkToLoad()
#             try:
#                 self.updateROIandNumAvg()
#             except DetectorConfigException:
#                 message = qtGui.QMessageBox()
#                 message.warning(self, \
#                                  WARNING_STR,\
#                                  "Trouble getting ROI or Num average " + \
#                                  "from the detector config file")
        else:
            message = qtGui.QMessageBox()
            message.warning(self, \
                             WARNING_STR,\
                             "The filename entered for the detector " + \
                             "configuration is invalid")
        
    def getOutputType(self):
        '''
        Get the output type to be used.
        '''
        return self.outTypeChooser.currentText()
    
    def _outputTypeChanged(self, typeStr):
        '''
        If the output is selected to be a simple grid map type then allow
        the user to select HKL as an output.
        :param typeStr: String holding the outpu type
        '''
        pass
        #
#         if typeStr == self.SIMPLE_GRID_MAP_STR:
#             self.hklCheckbox.setEnabled(True)
#         else:
#             self.hklCheckbox.setDisabled(True)
#             self.hklCheckbox.setCheckState(False)
