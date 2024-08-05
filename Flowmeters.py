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

# Loads settings from YAML file located in 'tools' directory  
settingsFile = os.path.dirname(os.path.realpath(__file__))+"/tools/settings.yaml" 
# settingsFile = "tools/settings.yaml" 
with open(settingsFile, 'r') as stream:
    settings = yaml.safe_load(stream)

class Worker(QtCore.QObject):

    running = pyqtSignal(bool)
    data = QtCore.pyqtSignal(object)

    @QtCore.pyqtSlot(str, str, int)

    def __init__(self): 

        QtCore.QThread.__init__(self)
        self.fm = fm.fm()
        self.running.emit(True)

    def getData(self, ):
        
        self.running.emit(True)
        
        fm0Data = self.fm.getData(channel = "ai0")
        fm1Data = self.fm.getData(channel = "ai1")   
        self.data.emit([fm0Data,fm1Data])  # Emit acquired data to update plot
 
        self.running.emit(False)

    def status(self) :

        self.running.emit()


class MainWindow(QtWidgets.QMainWindow):

    work_getData = QtCore.pyqtSignal(int)  # Define a signal that emits integers

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setContentsMargins(140, 40, 10, 10)
        self.setWindowTitle("Flowmeter 4.3") 
        self.setWindowIcon(QtGui.QIcon('icons/UHV Channels.ico'))

        # Worker thread for analog input reading
        self.worker = Worker()  
        self.worker_thread = QtCore.QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker.data.connect(self.getData)  # Signal to update plot with data        
        self.worker.running.connect(self.getStatus)
        self.work_getData.connect(self.worker.getData)
        self.worker_thread.start()       

        # Initial values for plotting 
        self.data0 = list()
        self.data1 = list()
        self.time = list()
        self.time0 = time.time()
         
        # Add labels to the plot 
        self.plot_analog = pg.PlotWidget() 
        self.setCentralWidget(self.plot_analog)
        font = QtGui.QFont("Arial", 15)
        self.plot_analog.setGeometry(150, 50, 600, 400)  # Adjust geometry as needed
        self.plot_analog.setBackground("w")
        self.plot_analog.setTitle("Flowmeter Input Data ", color = "k")
        self.plot_analog.setLabel('left', text='Voltage  (v)', color = "k")
        self.plot_analog.getAxis('bottom').setPen('black')
        self.plot_analog.getAxis("bottom").label.setFont(font)
        self.plot_analog.getAxis('bottom').setTextPen('black')
        self.plot_analog.getAxis("bottom").setTickFont(font)
        self.plot_analog.getAxis("bottom").setTickFont(font)
        self.plot_analog.getAxis("left").label.setFont(font)
        self.plot_analog.getAxis('left').setPen('black')
        self.plot_analog.getAxis('left').setTextPen('black')
        self.plot_analog.getAxis("left").setTickFont(font)
        self.plot_analog.setLabel('bottom', text='Time (s)', color = "k")          
        self.legend = self.plot_analog.addLegend()  


        fontsize_small = 10 
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
        self.checkbox_Chan0.move(10,100)    
        self.checkbox_Chan0.setStyleSheet('QLineEdit {background-color: white; color: black;}')
        self.checkbox_Chan0.setFont(QtGui.QFont('Arial', fontsize_small))

        self.combobox_Chan0 = QComboBox(self)
        self.combobox_Chan0.resize(132,30)
        self.combobox_Chan0.move(8,130)
        self.chan = self.combobox_Chan0.currentIndex()
        self.combobox_Chan0.addItems(settings['gases'])

        default_gas = "Oxygen (O2)"
        if default_gas in settings['gases']:
            self.combobox_Chan0.setCurrentText(default_gas)


        self.checkbox_Chan1 = QCheckBox(self)
        self.checkbox_Chan1.setText('Channel 1')
        self.checkbox_Chan1.setCheckable(True)
        self.checkbox_Chan1.setChecked(True)
        self.checkbox_Chan1.resize(100,30)
        self.checkbox_Chan1.move(10,230)    
        self.checkbox_Chan1.setStyleSheet('QLineEdit {background-color: white; color: black;}')
        self.checkbox_Chan1.setFont(QtGui.QFont('Arial', fontsize_small))

        self.combobox_Chan1 = QComboBox(self)
        self.combobox_Chan1.resize(132,30)
        self.combobox_Chan1.move(8,260)
        self.chan = self.combobox_Chan1.currentIndex()
        self.combobox_Chan1.addItems(settings['gases'])


        # Adding widgets to layout
        layout = QtWidgets.QVBoxLayout()

        # Create a main layout for central widget
        mainLayout = QtWidgets.QHBoxLayout()
        mainLayout.addLayout(layout)
        mainLayout.addWidget(self.plot_analog)

        centralWidget = QtWidgets.QWidget()
        centralWidget.setLayout(mainLayout)
        self.setCentralWidget(centralWidget)

        # Timer
        self.timer = QtCore.QTimer()
        self.timer.setInterval(500)  
        self.timer.timeout.connect(self.mainLoop)
        self.timer.start()


        self.show()            



    def mainLoop(self):    

        if self.checkbox_Chan0.isChecked() | self.checkbox_Chan1.isChecked() | (self.checkbox_Chan0.isChecked() & self.checkbox_Chan1.isChecked()) :
 
            self.button_go.setEnabled(True) 
            self.combobox_Chan0.setEnabled(True)
            self.combobox_Chan1.setEnabled(True)
            self.checkbox_Chan0.setEnabled(True)
            self.checkbox_Chan1.setEnabled(True) 
            self.checkbox_Save.setStyleSheet('QLineEdit {background-color: white; color: black;}')
  
            if self.button_go.isChecked(): 

                self.work_getData.emit(self)
                
                self.checkbox_Save.setStyleSheet('QLineEdit {background-color: white; color: black;}')
                

                if self.checkbox_Save.isChecked() :  # should make an if statement regard when there is only 0(index) to not get error for the -1
                    self.save()                 

                self.updatePlot()   

                self.button_go.setText('Stop')
                self.button_go.setStyleSheet("background-color: red")
                self.checkbox_Save.setEnabled(False) 

                if  self.go:
 
                    self.plot_analog.clear()

                    self.updatePlot()   

                    self.button_go.setText('Stop')
                    self.button_go.setStyleSheet("background-color: red")
                    self.checkbox_Save.setEnabled(False) 
                else :
                    self.reset() 
                    self.time0 = time.time() 
                
                self.go = True

            else: 
                self.button_go.setText('Start')
                self.button_go.setStyleSheet("background-color: green") 
                self.checkbox_Save.setEnabled(True)
                self.checkbox_Save.setText('Save')
                self.checkbox_Save.setStyleSheet('QLineEdit {background-color: white; color: black;}') 
                self.go = False 
                
        else:
            self.button_go.setEnabled(False)
            self.checkbox_Save.setEnabled(False)

            self.checkbox_Save.setStyleSheet('QLineEdit {background-color: grey; color: black;}')

 
    def save(self) :
     
        if not self.go:  

            self.go = True 
            self.reset()
            self.time0 = time.time()  

            now = datetime.now()
            folder = settings['data']['folder'] 
            folder = folder+f'{now.year:04d}'+'/'+f'{now.year:04d}'+'.'+f'{now.month:02d}'+'.'+f'{now.day:02d}'+'/'
            os.makedirs(folder, exist_ok=True) 


            file = 'prc'+f'{now.year:04d}'+f'{now.month:02d}'+f'{now.day:02d}'+'_'+f'{now.hour:02d}'+f'{now.minute:02d}'+f'{now.second:02d}'
            self.path = folder+file
            self.textbox_File.setText('File: '+file)
            print('Saving to file: '+self.path)

            with open(self.path+'.csv', "w", newline='') as TFile:

                TWriter = csv.writer(TFile, delimiter=',')

                if self.checkbox_Chan0.isChecked() & self.checkbox_Chan1.isChecked() :
                            
                    name0 = self.combobox_Chan0.currentText()  # Get the selected item from combobox_Chan0
                    name1 = self.combobox_Chan1.currentText()  # Get the selected item from combobox_Chan1

                    TWriter.writerow([name0, name1])

                    # if (len(self.data0) > 1 ) & (len(self.data1) > 1):
                    #     TWriter.writerow([self.data0[-1], self.data1[-1]])
                    #     print("getting data: " + str(self.data0[-1])) 

                elif self.checkbox_Chan0.isChecked():

                    name0 = self.combobox_Chan0.currentText()  # Get the selected item from combobox_Chan0 

                    TWriter.writerow([name0])

                    # if len(self.data0) > 1:
                    #     TWriter.writerow([self.data0[-1]])
                         
                        
                elif self.checkbox_Chan1.isChecked():
                    
                    name1 = self.combobox_Chan1.currentText()  # Get the selected item from combobox_Chan1
                    TWriter.writerow([name1])

                    # if len(self.data1) > 1:
                    #     TWriter.writerow([self.data1[-1]])
        
        else:

            with open(self.path+'.csv', "a", newline='') as TFile:
                TWriter = csv.writer(TFile, delimiter=',')

                if self.checkbox_Chan0.isChecked() & self.checkbox_Chan1.isChecked() : 
                    if (len(self.data0) > 1 ) & (len(self.data1) > 1):
                        TWriter.writerow([self.data0[-1], self.data1[-1]])

                elif self.checkbox_Chan0.isChecked():
                    if len(self.data0) > 1:
                        TWriter.writerow([self.data0[-1]])
                    
                elif self.checkbox_Chan1.isChecked():
                    
                    if len(self.data1) > 1:
                        TWriter.writerow([self.data1[-1]])

    def updatePlot(self):
        # Method to update plot with acquired data
        
        self.plot_analog.clear()

        if self.checkbox_Chan0.isChecked() & self.checkbox_Chan1.isChecked() :
            name0 = self.combobox_Chan0.currentText()  # Get the selected item from combobox_Chan0
            name1 = self.combobox_Chan1.currentText()  # Get the selected item from combobox_Chan1
          
            self.plot_analog.plot(self.time, self.data0, pen="r", name = name0)
            self.plot_analog.plot(self.time, self.data1, pen="k", name = name1)                
            self.plot_analog.plot(self.time, self.data0, symbol='+', pen="r", size=8, symbolBrush=pg.mkBrush('r'))
            self.plot_analog.plot(self.time, self.data1, symbol='+', pen="k", size=8, symbolBrush=pg.mkBrush('k'))
            self.combobox_Chan0.setEnabled(False)
            self.combobox_Chan1.setEnabled(False)

            self.checkbox_Chan0.setEnabled(False)
            self.checkbox_Chan1.setEnabled(False)

        elif self.checkbox_Chan0.isChecked():
            name0 = self.combobox_Chan0.currentText()  # Get the selected item from combobox_Chan0
          
            self.plot_analog.plot(self.time, self.data0, pen="r", name = name0)
            self.plot_analog.plot(self.time, self.data0, symbol='+', pen="r", size=8, symbolBrush=pg.mkBrush('r'))
            self.combobox_Chan0.setEnabled(False)
            self.combobox_Chan1.setEnabled(False)

            self.checkbox_Chan0.setEnabled(False)
            self.checkbox_Chan1.setEnabled(False)

        elif self.checkbox_Chan1.isChecked():
            name1 = self.combobox_Chan1.currentText()  # Get the selected item from combobox_Chan1
          
            self.plot_analog.plot(self.time, self.data1, pen="k", name = name1)
            self.plot_analog.plot(self.time, self.data1, symbol='+', pen="k", size=8, symbolBrush=pg.mkBrush('k'))   
            self.combobox_Chan0.setEnabled(False)
            self.combobox_Chan1.setEnabled(False)

            self.checkbox_Chan0.setEnabled(False)
            self.checkbox_Chan1.setEnabled(False)

    def getData(self,data) :


        if self.checkbox_Chan0.isChecked() & self.checkbox_Chan1.isChecked() :
            data0_mean = np.mean(data[0])
            data1_mean = np.mean(data[1])
            self.data0.append(data0_mean)
            self.data1.append(data1_mean)
            self.time.append(time.time() - self.time0)
            
        elif self.checkbox_Chan0.isChecked():
            data0_mean = np.mean(data[0]) 
            self.data0.append(data0_mean)
            self.time.append(time.time() - self.time0)

        elif self.checkbox_Chan1.isChecked():
            data1_mean = np.mean(data[1]) 
            self.data1.append(data1_mean)
            self.time.append(time.time() - self.time0)

    def getStatus(self, running):
        
        self.running = running

    def reset(self):

        self.data0 = []
        self.data1 = []
        self.time = []
        self.plot_analog.clear()

    def closeEvent(self, event):
        # Clean up when closing the application
        self.worker_thread.quit()
        self.worker_thread.wait()
   
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet())
    w = MainWindow()
    app.exec_()