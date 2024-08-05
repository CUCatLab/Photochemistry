import os
import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import pyqtgraph as pg
import qdarkstyle
from datetime import datetime
import sys
import csv
import yaml
import time
import matheson_fm as fm
import re
from srsinst.rga import RGA100 as srs_rga

settingsFile = os.path.dirname(os.path.realpath(__file__))+"/tools/settings.yaml" 
# settingsFile = "tools/settings.yaml" 
with open(settingsFile, 'r') as stream:
    settings = yaml.safe_load(stream)

class Worker(QtCore.QObject):

    running = pyqtSignal(bool)
    data = QtCore.pyqtSignal(object)
    # go = pyqtSignal(bool) ###
    masses = pyqtSignal(object)


    @QtCore.pyqtSlot(str, str, int)

    def __init__(self): 

        QtCore.QThread.__init__(self)
        self.fm = fm.fm()
        self.running.emit(True)
        self.rgaOn = False ###
        self.masses = []

    def getData(self):
        
        self.running.emit(True)
        
        fm0Data = self.fm.getData(channel = "ai0")
        fm1Data = self.fm.getData(channel = "ai1") 
        masses = self.masses
        if self.rgaOn :
            Pi_values = list()
            for mass in masses :
                intensity = self.rga.scan.get_multiple_mass_scan(mass)
                intensity_in_torr = self.rga.scan.get_partial_pressure_corrected_spectrum(intensity)
                intensity_in_torr = np.array(intensity_in_torr)
                Pi_values.append(intensity_in_torr[0])
        else :
            Pi_values = np.zeros((len(masses)))
        self.data.emit([[fm0Data,fm1Data],Pi_values,masses])
        self.running.emit(False)

    def setMasses(self,masses) : 
        self.masses=masses

    def startRGA(self) : 

        if not self.rgaOn :
            self.running.emit(True)
            print('Turning on SRS RGA.')
            self.rga = srs_rga('serial', 'COM'+str(settings['srs']['rga100']['com']), 28800)
            self.rga.ionizer.set_parameters(70, 12, 90)
            self.rga.filament.turn_on()
            self.rga.cem.turn_on()
            print('Emission current: '+str(self.rga.ionizer.emission_current)+' A')
            print('CEM Voltage: '+str(self.rga.cem.voltage)+' V')
            print('SRS RGA ready.')
            self.rgaOn = True
            self.running.emit(False)
    
    def stopRGA(self) :
        
        if self.rgaOn :
            self.running.emit(True)
            print('Turning off SRS RGA.')
            self.rga.cem.turn_off()
            self.rga.filament.turn_off()
            self.rga.ionizer.set_parameters(0, 0, 0)
            print('Emission current: '+str(self.rga.ionizer.emission_current)+' A')
            print('CEM Voltage: '+str(self.rga.cem.voltage)+' V')
            self.rga.disconnect()
            print('SRS RGA off.')
            self.rgaOn = False
            self.running.emit(False)

    def status(self) :

        self.running.emit()


class MainWindow(QtWidgets.QMainWindow):

    work_getData = QtCore.pyqtSignal(int)  # Define a signal that emits integers
    work_setMasses = pyqtSignal(object) ###
    work_startRGA = pyqtSignal(object)
    work_stopRGA = pyqtSignal(object)

    def __init__(self): 

        super(MainWindow, self).__init__()
        self.setContentsMargins(140, 40, 10, 10)
        self.setWindowTitle("FmMassSpec 5.2") 
        self.setWindowIcon(QtGui.QIcon('icons/UHV Channels.ico')) # ask about this

        # Worker thread
        self.worker = Worker()  
        self.worker_thread = QtCore.QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker.data.connect(self.getData)  # Signal to update plot with data        
        self.worker.running.connect(self.getStatus)
        self.work_getData.connect(self.worker.getData)
        self.work_setMasses.connect(self.worker.setMasses) ###
        self.work_startRGA.connect(self.worker.startRGA)
        self.work_stopRGA.connect(self.worker.stopRGA)
        self.worker_thread.start()
        self.work_getData.emit(self)

        #  TPD Variables
        self.go = False
        self.masses = list()
        self.Pi = np.nan
        self.Pi_array = list()  
        self.rgaOn = False
        self.t = np.nan
        self.t0 = time.time()
        self.t_array = list()
        self.loops = 0
        self.data0 = list()
        self.data1 = list()

        # TPD Settings (might not need)
        fontsize_small= 10  

        # TPD Plot
        self.plot = pg.PlotWidget()
        # self.setCentralWidget(self.plot)
        font = QFont("Arial", fontsize_small)
        self.plot.setBackground('white')
        self.plot.setLabel("left", "Partial Pressure (Torr)")
        self.plot.setLabel("bottom", "Time (s)")
        self.plot.setTitle("Mass Spectroscopy Output Data", color = "k",size=f'{fontsize_small}pt')
        self.plot.getAxis('bottom').setPen('black')
        self.plot.getAxis("bottom").label.setFont(font)
        self.plot.getAxis('bottom').setTextPen('black')
        self.plot.getAxis("bottom").setTickFont(font)
        self.plot.getAxis("left").label.setFont(font)
        self.plot.getAxis('left').setPen('black')
        self.plot.getAxis('left').setTextPen('black')
        self.plot.getAxis("left").setTickFont(font)
        self.legend = self.plot.addLegend()

        # Add labels to the plot 
        self.plot_fm = pg.PlotWidget()  
        font = QtGui.QFont("Arial", fontsize_small) 
        self.plot_fm.setBackground("w")
        self.plot_fm.setTitle("Flowmeter Input Data ", color = "k",size=f'{fontsize_small}pt')
        self.plot_fm.setLabel('left', text='Voltage  (v)', color = "k")
        self.plot_fm.getAxis('bottom').setPen('black')
        self.plot_fm.getAxis("bottom").label.setFont(font)
        self.plot_fm.getAxis('bottom').setTextPen('black')
        self.plot_fm.getAxis("bottom").setTickFont(font)
        self.plot_fm.getAxis("bottom").setTickFont(font)
        self.plot_fm.getAxis("left").label.setFont(font)
        self.plot_fm.getAxis('left').setPen('black')
        self.plot_fm.getAxis('left').setTextPen('black')
        self.plot_fm.getAxis("left").setTickFont(font)
        self.plot_fm.setLabel('bottom', text='Time (s)', color = "k")          
        self.legend_fm = self.plot_fm.addLegend()  

        # Input labels
        self.label_Mass = QLabel('Masses',self) 
        self.label_Mass.move(10, 315)
        self.label_Mass.resize(100,30)
        self.label_Mass.setFont(QFont('Arial', fontsize_small))
        self.label_Mass.setStyleSheet("QLabel  {color : white; }")

        # Textboxes
        self.textbox_masses = QLineEdit(settings['srs']['rga100']['masses'],self)
        self.textbox_masses.move(10, 345)
        self.textbox_masses.resize(100,30)
        self.textbox_masses.setStyleSheet(("QLabel  {color : black; }"))
        self.textbox_masses.adjustSize()

        self.button_RGA = QPushButton('Turn on MS',self)
        self.button_RGA.setCheckable(True)
        self.button_RGA.setChecked(False)
        self.button_RGA.resize(70,27)
        self.button_RGA.move(140,10)  
        self.button_RGA.setStyleSheet("background-color:green")

        # Start/Stop button
        self.go = False
        self.button_go = QPushButton(self)
        self.button_go.setText('Start')
        self.button_go.setCheckable(True)
        self.button_go.resize(100, 30)
        self.button_go.move(10, 460)
        self.button_go.setStyleSheet("background-color: green") 
        
        self.checkbox_Save = QCheckBox(self)
        self.checkbox_Save.setText('Save')        
        self.checkbox_Save.setCheckable(True)
        self.checkbox_Save.setChecked(True)
        self.checkbox_Save.resize(100, 30)
        self.checkbox_Save.move(10, 380)
        self.checkbox_Save.setStyleSheet('QLineEdit {background-color: white; color: black;}')
        self.checkbox_Save.setFont(QtGui.QFont('Arial', fontsize_small))

        self.textbox_File = QLabel(self)
        self.textbox_File.move(350,10)
        self.textbox_File.resize(400,30)
        self.textbox_File.setFont(QtGui.QFont('Arial', fontsize_small))
        self.textbox_File.setStyleSheet('QLabel {color: white;}') #background-color: white
        self.textbox_File.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
 
        self.checkbox_Chan0 = QCheckBox(self)
        self.checkbox_Chan0.setText(' Channel 0')
        self.checkbox_Chan0.setCheckable(True)
        self.checkbox_Chan0.setChecked(True)
        self.checkbox_Chan0.resize(100,30)
        self.checkbox_Chan0.move(10,80)    
        self.checkbox_Chan0.setStyleSheet('QLineEdit {background-color: white; color: black;}')
        self.checkbox_Chan0.setFont(QtGui.QFont('Arial', fontsize_small))

        self.combobox_Chan0 = QComboBox(self)
        self.combobox_Chan0.resize(132,30)
        self.combobox_Chan0.move(8,110)
        self.chan = self.combobox_Chan0.currentIndex()
        self.combobox_Chan0.addItems(settings['gases'])

        self.checkbox_Chan1 = QCheckBox(self)
        self.checkbox_Chan1.setText('Channel 1')
        self.checkbox_Chan1.setCheckable(True)
        self.checkbox_Chan1.setChecked(True)
        self.checkbox_Chan1.resize(100,30)
        self.checkbox_Chan1.move(10,200)    
        self.checkbox_Chan1.setStyleSheet('QLineEdit {background-color: white; color: black;}')
        self.checkbox_Chan1.setFont(QtGui.QFont('Arial', fontsize_small))

        self.combobox_Chan1 = QComboBox(self)
        self.combobox_Chan1.resize(132,30)
        self.combobox_Chan1.move(8,230)
        self.chan = self.combobox_Chan1.currentIndex()
        self.combobox_Chan1.addItems(settings['gases'])
        if len(settings['gases']) > 1 :
            self.combobox_Chan1.setCurrentText(settings['gases'][1])

        # Adding widgets to layout
        layout = QtWidgets.QVBoxLayout()

        # Create a main layout for top widget
        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addLayout(layout)
        mainLayout.addWidget(self.plot, 5)
        mainLayout.addWidget(self.plot_fm, 3) 

        centralWidget = QtWidgets.QWidget()
        centralWidget.setLayout(mainLayout)
        self.setCentralWidget(centralWidget) 
 
        # Timer
        self.timer = QtCore.QTimer()
        self.timer.setInterval(500)  
        self.timer.timeout.connect(self.mainLoop)
        self.timer.start()

        # Mass spec Initialize functions
        self.setMasses()

        self.show()            

    def mainLoop(self):    

        if self.button_RGA.isChecked() :
            self.button_RGA.setText('Turn off RGA')
            self.button_RGA.setStyleSheet("background-color:red")
            if self.rgaOn == False :
                self.startRGA()
            self.rgaOn = True
        else :
            self.button_RGA.setText('Turn on RGA')
            self.button_RGA.setStyleSheet("background-color:green")
            if self.rgaOn == True :
                self.stopRGA()
            self.rgaOn = False
  
        if self.button_go.isChecked(): 
            if self.rgaOn :
                self.button_go.setText('Stop')
                self.button_go.setStyleSheet("background-color: red")
                self.button_RGA.setEnabled(False)
                self.checkbox_Save.setEnabled(False)
                self.combobox_Chan0.setEnabled(False)
                self.combobox_Chan1.setEnabled(False)
                self.checkbox_Chan0.setEnabled(False)
                self.checkbox_Chan1.setEnabled(False)
                self.textbox_masses.setEnabled(False)

                if not self.go :

                    self.reset()
                    self.t0 = time.time() 
                    self.setMasses() # ???   do we need them here? (trying to merge fm and tpd) 
                    self.lines = list()
                    
                    for idx, mass in enumerate(self.masses) :
                        self.lines.append(self.plot.plot((),(),name='Mass '+str(mass),symbol="+",symbolPen=pg.mkPen(pg.intColor(idx)),symbolBrush=pg.intColor(idx),pen=pg.mkPen(pg.intColor(idx), width=1)))
                    legendLabelStyle = {'color': 'black', 'size': '12pt'}

                    for item in self.legend.items:
                        for single_item in item:
                            if isinstance(single_item, pg.graphicsItems.LabelItem.LabelItem):
                                single_item.setText(single_item.text, **legendLabelStyle) 

                    self.go = True
                    
                if not self.running :
                    self.work_getData.emit(self)
                    self.updatePlot()
                    if self.checkbox_Save.isChecked() :
                        self.save()

            else :

                print('Please turn on RGA.')
                self.button_go.setChecked(False)
                
        else:
            self.go = False
            self.button_go.setText('Start')
            self.button_go.setStyleSheet("background-color:green")
            self.button_RGA.setEnabled(True)
            self.checkbox_Save.setEnabled(True)
            self.combobox_Chan0.setEnabled(True)
            self.combobox_Chan1.setEnabled(True)
            self.checkbox_Chan0.setEnabled(True)
            self.checkbox_Chan1.setEnabled(True)
            self.textbox_masses.setEnabled(True)
    
    def getData(self,data) :

        # Time data
        self.t = round(time.time() - self.t0,2)
        self.t = float(self.t)
        self.t_array.append(self.t)

        string = 'Time (s): '+str(self.t)

        # Flow meter data            
        if self.checkbox_Chan0.isChecked():
            data0_mean = np.mean(data[0][0]) 
            self.data0.append(data0_mean)
            string += ', Chan0: '+str(data0_mean)
        if self.checkbox_Chan1.isChecked():
            data1_mean = np.mean(data[0][1]) 
            self.data1.append(data1_mean)
            string += ', Chan1: '+str(data1_mean)

        # Mass spec data
        self.Pi = data[1]
        for idx, Pi in enumerate(self.Pi) :
            self.Pi[idx] = float(f'{float(Pi):.4e}')
        if len(self.Pi) == len(self.masses) :
            for idx, Pi in enumerate(self.Pi) :
                if idx < len(self.Pi_array):
                    self.Pi_array[idx].append(Pi)
            if self.button_go.isChecked():
                for idx,mass in enumerate(self.masses) :
                    string += ', Mass '+str(mass)+': '+f'{self.Pi[idx]:.2e}'+' Torr'

        # Display data in terminal
        if self.button_go.isChecked():
            print(string)
 
    def updatePlot(self):

        if len(self.t_array) != 0 :
            # Plot mass spec data
            for idx, line in enumerate(self.lines) :
                self.lines[idx].setData(self.t_array,self.Pi_array[idx])
                
            self.plot_fm.clear()
            # Plot flow meter data
            if self.checkbox_Chan0.isChecked() :
                name0 = self.combobox_Chan0.currentText()  # Get the selected item from combobox_Chan0
                self.plot_fm.plot(self.t_array, self.data0, symbol='+', pen="r", size=8, symbolBrush=pg.mkBrush('r'), name = name0)
            
            if self.checkbox_Chan1.isChecked() :
                name1 = self.combobox_Chan1.currentText()  # Get the selected item from combobox_Chan1      
                self.plot_fm.plot(self.t_array, self.data1, symbol='+', pen="k", size=8, symbolBrush=pg.mkBrush('k'), name = name1)
 
    def save(self) :

        try :
            
            data = [self.t]
            for Pi in self.Pi :
                data.append(Pi) 
            with open(self.path+'.csv', "a", newline='') as TFile:
                TWriter = csv.writer(TFile, delimiter=',') 
                
                if self.checkbox_Chan0.isChecked() & self.checkbox_Chan1.isChecked() : 
                    if (len(self.data0) > 1 ) & (len(self.data1) > 1):
                        TWriter.writerow(data + [self.data0[-1], self.data1[-1]] ) 
                elif self.checkbox_Chan0.isChecked():
                    if len(self.data0) > 1:
                        TWriter.writerow(data + [self.data0[-1]])
                    
                elif self.checkbox_Chan1.isChecked():
                    
                    if len(self.data1) > 1:
                        TWriter.writerow(data + [self.data1[-1]])

        except :

            now = datetime.now()
            folder = settings['data']['folder'] 
            folder = folder+f'{now.year:04d}'+'/'+f'{now.year:04d}'+'.'+f'{now.month:02d}'+'.'+f'{now.day:02d}'+'/'
            os.makedirs(folder, exist_ok=True) 
            file = 'prc'+f'{now.year:04d}'+f'{now.month:02d}'+f'{now.day:02d}'+'_'+f'{now.hour:02d}'+f'{now.minute:02d}'+f'{now.second:02d}'
            self.path = folder+file
            self.textbox_File.setText('File: '+file)
            print('Saving to file: '+self.path)

            # TPD - Save Parameters
            par = list()
            par = {}
            par['t_unit'] = 's'
            par['Pi_unit'] = 'Torr'
            with open(self.path+'.yml', "w") as outfile: # Double check/Ask
                yaml.dump(par, outfile, default_flow_style=False)
            
            header  = ['Time (s)']
            for mass in self.masses : # then include the Mass 12(5,6,7,8,etc.)
                header.append('Mass '+str(mass)) 
 

            with open(self.path+'.csv', "w", newline='') as TFile:

                TWriter = csv.writer(TFile, delimiter=',')

                if self.checkbox_Chan0.isChecked() & self.checkbox_Chan1.isChecked() :
                            
                    name0 = self.combobox_Chan0.currentText()  # Get the selected item from combobox_Chan0
                    name1 = self.combobox_Chan1.currentText()  # Get the selected item from combobox_Chan1

                    TWriter.writerow(header + [name0, name1]) 

                elif self.checkbox_Chan0.isChecked():

                    name0 = self.combobox_Chan0.currentText()  # Get the selected item from combobox_Chan0  
                    TWriter.writerow(header + [name0]) 
                        
                elif self.checkbox_Chan1.isChecked():
                    
                    name1 = self.combobox_Chan1.currentText()  # Get the selected item from combobox_Chan1
                    TWriter.writerow(header + [name1]) 
 
    
    def getStatus(self, running):
        
        self.running = running

    def startRGA(self) :

        self.work_startRGA.emit(self)

    def stopRGA(self) :

        self.work_stopRGA.emit(self)
    
    def setMasses(self) :

        masses = self.textbox_masses.text()
        masses = re.split(';|,',masses)
        for idx,mass in enumerate(masses) :
            masses[idx] = float(mass)
        self.masses = masses
        self.work_setMasses.emit(masses)
        self.Pi_array = list()  
        for mass in masses :
            self.Pi_array.append(list())
 
    def reset(self):

        # TPD
        self.t_array = list()
        self.Pi_array = list() 
        self.data0 = []
        self.data1 = []
        self.time = []
        self.plot.clear()
        self.plot_fm.clear()

    def closeEvent(self, event):
        # Clean up when closing the application
        self.worker_thread.quit()
        self.worker_thread.wait()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet())
    w = MainWindow()
    app.exec_()