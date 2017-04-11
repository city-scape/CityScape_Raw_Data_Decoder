#!/usr/bin/env python

from Tkinter import *
from ttk import *
import tkFileDialog
import tkMessageBox
import sys
import argparse
import psdFile_pb2
import os.path
import time
import matplotlib.pyplot as plt
import numpy as np
import scipy.io as sio
import zlib

#Store processed data.
class ProcessedData:
	
	def __init__(self):
		self.station_config = ""
		self.data_length = -1
		self.freq_s = -1
		self.freq_e = -1
		self.freq = []
		self.psd_avg_sum = []
		self.psd_avg_sum_cnt = 0
		self.psd_max = []
		self.psd_min = []

#Decompress (before parsing)
def decompress (dat):
	return zlib.decompress(dat,-15)

#Converts "Reading Kind" enum to String.
#("Reading Kind" enums is an enumeratation type used by the PSD scan file to identify the 
#type of the data, such as "average observed power", "minimum observed power", or "maximum observed power".)
#input : integer "reading_kind"
#output : string representation.
def get_reading_kind(reading_kind):
	if reading_kind == 0:
		return "Average"
	elif reading_kind == 1:
		return "Minimum"
	elif reading_kind == 2:
		return "Maximum"
	elif reading_kind == 3:
		return "StdDev of Average"
	elif reading_kind == 4:
		return "StdDev of Minimum"
	elif reading_kind == 5:
		return "StdDev of Maximum"
	elif reading_kind == 6:
		return "Avg of Minimum"
	elif reading_kind == 7:
		return "Avg of Maximum"
	else:
		return "?????????"

#Converts the data (Q format fixed floating point) to the proper floating point decibel representation.
#See https://en.wikipedia.org/wiki/Q_(number_format) for Q format.
#The output data will be an array of floating point numbers representing power spectral density (in dB).
#input : numpy int[] of PSD data
#output : double[] data
def data_to_float_decibel(ary):
	result = np.zeros((len(ary),1),dtype=np.float32)

	for i in range(0, len(ary)-1):
		#Fortunately, the expression will be almost always true (therefore performance drop from the branch hazard is negligible).
		if ary[i] != -32768:	#Short.Min_VALUE = NaN (for this particular implementation).
			result[i] = ary[i] / float(1<<7) #expected equation..
		else:
			result[i] = np.nan

	return result

#Determines the time scale used by the timestamp.
#Must be multiplied to the timestamp to get second-scale time.
#Only handles minute-scale and hour-scale, since other scales are apparantly not used the PSD files.
#in : time scale type, in enum.
#out : time scale (returned value * timestamp value = POSIX timestamp).
def determine_timescale(scale):
	time_scale = 0
	if scale == psdFile_pb2.Timestamp.DAYS:	#days
		time_scale = 86400		
	elif scale == psdFile_pb2.Timestamp.HOURS:	#Hours
		time_scale = 3600
	elif scale == psdFile_pb2.Timestamp.MINUTES: #Minutes
		time_scale = 60
	elif scale == psdFile_pb2.Timestamp.SECONDS: #Seconds
		time_scale = 1
	elif scale == psdFile_pb2.Timestamp.MILLISECONDS: #Minutes
		time_scale = 1.0/1000
	elif scale == psdFile_pb2.Timestamp.TICKS:	#ticks
		time_scale = 1.0/10000000
	else:
		raise Exception('Unexpected timestamp scale.')		
		
	return time_scale

#Stage 1
#Calculate FFT size, start - end freq, etc.
def process_stage1(data,pdinst):
	pd.station_config = str(data.Config).replace("\\n","\n\t").replace("\\r","").replace("\\t","\t")
	if len(data.SpectralPsdData) < 1:
		raise Exception('0 Length Data')
	else:
		pd.data_length = len(data.SpectralPsdData[0].OutputDataPoints)
		pd.freq_s = (data.SpectralPsdData[0].StartFrequencyHz)/1e6
		pd.freq_e = (data.SpectralPsdData[0].StopFrequencyHz)/1e6
		pd.freq = np.transpose(np.linspace(pd.freq_s,pd.freq_e,pd.data_length))
		pd.psd_avg_sum = np.zeros((pd.data_length,1),dtype=np.float32)
		pd.psd_max = np.subtract (np.zeros((pd.data_length,1),dtype=np.float32) , float('inf'))
		pd.psd_min = np.add (np.zeros((pd.data_length,1),dtype=np.float32) , float('inf'))
		
#Process the data points.
def process_stage2(data,pd):

	#for each data block
	for data_block in data.SpectralPsdData:				
		
		#Convert data points from Q format to IEEE754 floating point.
		#!!!!!slow part!!!!!
		db_data = data_to_float_decibel(data_block.OutputDataPoints)
				
		#Assign data
		reading_kind = data_block.Reading_Kind
		if reading_kind == 0:	#Data is for Average
			pd.psd_avg_sum_cnt = pd.psd_avg_sum_cnt  + 1
			pd.psd_avg_sum = np.add(pd.psd_avg_sum,db_data)
		elif reading_kind == 1:	#Data is for min hold
			pd.psd_min = np.minimum(pd.psd_min,db_data)
		elif reading_kind == 2:	#Data is for max hold
			pd.psd_max = np.maximum(pd.psd_max,db_data)
		
		#plot the result (if requested).
		#if plot_psd == cnt or plot_psd == 0:
		#	freq_mhz = np.linspace(data_block.StartFrequencyHz/1e6,data_block.StopFrequencyHz/1e6,num=len(data_block.OutputDataPoints))
		#	plt.plot(freq_mhz,db_data[0:])
		#	plt.xlabel('frequency (MHz)')
		#	plt.title('PSD plot. Timestamp:' + str(data_block.Time_stamp.value) + ', Type : ' + get_reading_kind(data_block.Reading_Kind))
		#	plt.ylabel('PSD (dB)')
		#	plt.show()

#Plots PSD (tk button callback)
def plot_psd(pd,start,end,ymin,ymax,plot_min,plot_avg,plot_max):
	try:		
		start_freq = float(start)
		end_freq = float(end)
		ymin = float(ymin)
		ymax = float(ymax)
		
		if (start_freq < pd.freq_s) or (start_freq > pd.freq_e) or (end_freq < pd.freq_s) or (end_freq > pd.freq_e):
			raise Exception ('Error: Start / End Freq Mismatch')
		if start_freq > end_freq:
			raise Exception ('Error: End Freq > Start Freq')

		array_pos_start = int(((start_freq - pd.freq_s) / (pd.freq_e - pd.freq_s)) * pd.data_length)
		array_pos_end = int(((end_freq - pd.freq_s) / (pd.freq_e - pd.freq_s)) * pd.data_length)
		
		plt.figure()
		if(plot_avg):
			plt.plot(pd.freq[array_pos_start:array_pos_end+1],pd.psd_avg_sum[array_pos_start:array_pos_end+1] / pd.psd_avg_sum_cnt, 'b', label="Average")
		if(plot_max):
			plt.plot(pd.freq[array_pos_start:array_pos_end+1],pd.psd_max[array_pos_start:array_pos_end+1] , 'r', label="Max Hold")
		if(plot_min):
			plt.plot(pd.freq[array_pos_start:array_pos_end+1],pd.psd_min[array_pos_start:array_pos_end+1] , 'k', label="Min Hold")
			
		plt.axis([start_freq,end_freq,ymin,ymax])
		plt.legend(loc='upper center', shadow=True)
		plt.xlabel('frequency (MHz)')
		plt.title('PSD plot')
		plt.ylabel('PSD (dBm/Bin)')
		plt.show()
		
	except Exception as a:
		tkMessageBox.showinfo(message="Plot failed (Check your inputs arguments). Exception Message : " + str(a))

#Exports to .mat (tk button callback)
def export_mat(pd,start,end,ymin,ymax):
	try:		
		start_freq = float(start)
		end_freq = float(end)
		ymin = float(ymin)
		ymax = float(ymax)
		
		if (start_freq < pd.freq_s) or (start_freq > pd.freq_e) or (end_freq < pd.freq_s) or (end_freq > pd.freq_e):
			raise Exception ('Error: Start / End Freq Mismatch')
		if start_freq > end_freq:
			raise Exception ('Error: End Freq > Start Freq')

		array_pos_start = int(((start_freq - pd.freq_s) / (pd.freq_e - pd.freq_s)) * pd.data_length)
		array_pos_end = int(((end_freq - pd.freq_s) / (pd.freq_e - pd.freq_s)) * pd.data_length)
		
		
		afn = {}
		afn['defaultextension'] = '.mat'
		afn['filetypes'] = [('Matlab Data File','.mat')]
		fpath = tkFileDialog.asksaveasfilename(**afn)
		
		sio.savemat(fpath,{'Freq':pd.freq[array_pos_start:array_pos_end+1],'Avg':pd.psd_avg_sum[array_pos_start:array_pos_end+1] / pd.psd_avg_sum_cnt , 'Max_Hold':pd.psd_max[array_pos_start:array_pos_end+1] ,'Min_Hold':pd.psd_min[array_pos_start:array_pos_end+1]})	
		
	except Exception as a:
		tkMessageBox.showinfo(message="Export failed (Check your inputs arguments). Exception Message : " + str(a))

#--------------------------------------------------
# Main routine (int main() equivalent)
#--------------------------------------------------

#init tk
root = Tk()
root.wm_title("Cityscape PSD Data File Plotter (For Testing)")

#add tabs
note = Notebook(root)
tab1 = Frame(note)
tab2 = Frame(note)
note.add(tab1, text='Plot')
note.add(tab2, text='Config String')
note.pack()

label_0= Label(tab1, text = "Processing...")
label_0.grid(row=0,column=0,sticky="W")

#File Open dialog
afn = {}
afn['defaultextension'] = '.dsox'
afn['filetypes'] = [('Cityscape Aggregated PSD File','.dsox')]
fpath = tkFileDialog.askopenfilename(**afn)


#open file.
f = open(fpath,"rb");

#Attempt decompression. If fails, assume decompressed data and just push that into the Protobuf decoder.
f_str = f.read()
f.close()
try:
	decompress_out = decompress (f_str)
	f_str = decompress_out
except Exception:
	pass
	
#Parse.
scan_file_read = psdFile_pb2.ScanFile()
scan_file_read.ParseFromString(f_str)

#process.
pd = ProcessedData()
process_stage1(scan_file_read,pd)
process_stage2(scan_file_read,pd)

#display config string
config_text = Text(tab2)
config_text.insert(INSERT,pd.station_config)
config_text.grid(row=0,column=0,sticky="NSWE")
config_text['yscrollcommand'] = Scrollbar(tab2, command=config_text.yview).grid(row=0,column=1,sticky="SN")

#Display plot fields
#Freq
label_0['text'] = "Start Freq (MHz)"	#re-use pre-created object
Label(tab1, text = "End Freq (MHz)").grid(row=1,column=0,sticky="W")

entry_freq_start  = Entry(tab1)
entry_freq_stop  = Entry(tab1)

entry_freq_start.grid(row=0,column=1)
entry_freq_stop.grid(row=1,column=1)

entry_freq_start.insert(0,pd.freq_s)
entry_freq_stop.insert(0,pd.freq_e)

#Axis
Label(tab1, text = "Y_min").grid(row=2,column=0,sticky="W")
Label(tab1, text = "Y_max").grid(row=3,column=0,sticky="W")

entry_ymin  = Entry(tab1)
entry_ymax  = Entry(tab1)

entry_ymin.grid(row=2,column=1)
entry_ymax.grid(row=3,column=1)

entry_ymin.insert(0,"-140")
entry_ymax.insert(0,"0")

#Checkbox to turn on/off min max avg from plot.
c_min_var = IntVar(value=0)
c_avg_var = IntVar(value=1)
c_max_var = IntVar(value=1)

c_min = Checkbutton(tab1, text="Min Hold", variable=c_min_var)
c_avg = Checkbutton(tab1, text="Average", variable=c_avg_var)
c_max = Checkbutton(tab1, text="Max Hold", variable=c_max_var)

c_min.grid(row=4,column=0)
c_avg.grid(row=4,column=1)
c_max.grid(row=4,column=2)

#button
butt = Button(tab1, text="Plot", command= lambda: plot_psd(pd,entry_freq_start.get(),entry_freq_stop.get(),entry_ymin.get(),entry_ymax.get(),c_min_var.get(),c_avg_var.get(),c_max_var.get()))	#:-|
butt.grid(row=5,column=0)

butt = Button(tab1, text="Export to Matlab", command= lambda: export_mat(pd,entry_freq_start.get(),entry_freq_stop.get(),entry_ymin.get(),entry_ymax.get()))	#:-|
butt.grid(row=5,column=1)

#Display some properties
Label(tab1, text = "Start Freq (MHz):"+str(pd.freq_s)+"   ").grid(row=6,column=0,sticky="W")
Label(tab1, text = "End Freq (MHz):"+str(pd.freq_e)+"   ").grid(row=6,column=1,sticky="W")

sensor_cnt = 1

#Display sensor configs (can have multiple sensors)
for sensor in scan_file_read.Config.EndToEndConfiguration.RFSensorConfigurations:	
	#Get info
	GainLevel = sensor.Gain
	AntennaPort = sensor.AntennaPort
	ScanPattern = sensor.ScanPattern
	EffSampRate = sensor.EffectiveSamplingRateHz
	SnapshotSize = sensor.SamplesPerSnapshot
	AddnTuneDelay = sensor.AdditionalTuneDelay
	
	#Display
	Label(tab1, text = "Sensor #" + str(sensor_cnt)).grid(row=4+(sensor_cnt*3),column=0,sticky="W")
	Label(tab1, text = "Gain:"+str(GainLevel)+"   ").grid(row=5+(sensor_cnt*3),column=0,sticky="W")
	Label(tab1, text = "Antenna Port:"+AntennaPort+"   ").grid(row=5+(sensor_cnt*3),column=1,sticky="W")
	Label(tab1, text = "Scan Pattern:"+ScanPattern+"   ").grid(row=5+(sensor_cnt*3),column=2,sticky="W")
	Label(tab1, text = "Effective Samp Rate:"+str(EffSampRate)+"   ").grid(row=6+(sensor_cnt*3),column=0,sticky="W")
	Label(tab1, text = "Samples Per Snapshot:"+str(SnapshotSize)+"   ").grid(row=6+(sensor_cnt*3),column=1,sticky="W")
	Label(tab1, text = "Additional Tune Delay:"+str(AddnTuneDelay)+"   ").grid(row=6+(sensor_cnt*3),column=2,sticky="W")
	
	sensor_cnt = sensor_cnt + 1

#start tk loop
root.mainloop()
