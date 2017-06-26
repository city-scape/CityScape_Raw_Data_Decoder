#!/usr/bin/env python

#This script accepts a Microsoft Spectrum Observatory PSD scan file, processes and displays summarized results.

#Usage : ./psdFile_process.py target_file (Unix with execute permission)
#         python psdFile_process.py target_file (Windows or with non-execute permission)
#Requirements: Python 2.7 with Protoc Python bindings (Ubuntu package name: python-protobuf). psdFile_pb2.py must be present in the same directory.

#See: https://developers.google.com/protocol-buffers/docs/pythontutorial

#Last-modified: Mar 25, 2017 (Kyeong Su Shin)
#TODO : refactoring (getting quite dirty..)

import sys
import argparse
import psdFile_pb2
import os.path
import time
import matplotlib.pyplot as plt
import numpy as np
import scipy.io as sio
import zlib

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
	result = np.zeros(len(ary))

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
	
#Print out the "config" section of the data file and call "print_data_block_summary"
#to print out the summarized version of the data blocks.
#input: psdFile_pb2.ScanFile()
#output: none (directly prints out to stdout)
def print_file_summary(data,plot_psd,dump_csv,dump_mat):
	
	#Print out station configurations
	print "\n \n \n \n -----------------CONFIG BLOCK-----------------"
	#"replace" statements are not necessary, but they are used to re-format the "HardwareConfiguration" 
	#section of the config metadata (which has \\r, \\n, and \\t instead of their actual ASCII codes).
	print str(data.Config).replace("\\n","\n\t").replace("\\r","").replace("\\t","\t")
	print "---------------CONFIG BLOCK END---------------\n \n \n \n"

	#Print out summary of the data blocks.
	print "--------------DATA BLOCK SUMMARY--------------"
	print_data_block_summary(data,plot_psd,dump_csv,dump_mat)
	print "------------DATA BLOCK SUMMARY END------------ \n "

#Print out summary of the data blocks.
#input: psdFile_pb2.ScanFile()
#output: none (directly prints out to stdout)
def print_data_block_summary(data,plot_psd,dump_csv,dump_mat):
	cnt = 0						#total number of data blocks present in a file.
	data_cnt_sum = 0			#total number of data points (=blocks * points per each block).
	min_freq = float("inf")	#minimum frequency observed.
	max_freq = -1				#maximum frequency observed.
	
	#for each data block
	for data_block in data.SpectralPsdData:
		#increment block counter.
		cnt = cnt + 1
		
		#determine timestamp scale. (I think both minute-scale and hour-scale timestamps are used for these files, I don't know why.)
		time_scale = determine_timescale(data_block.Time_stamp.scale)
		
		#print out a summary. (comment out to reduce amount of information printed out)
		print "Block " + str(cnt) + " : "
		print "\t timestamp : " + time.ctime(data_block.Time_stamp.value*time_scale  + time.altzone) 	#Python automatically adjusts the timezone, but that is not desirable. So, roll-back by adding back the time offset "time.altzone". 
		print "\t Start Freq : " + str((data_block.StartFrequencyHz)/1e6) + "Mhz"
		print "\t Stop Freq : " + str((data_block.StopFrequencyHz)/1e6) + "Mhz"
		print "\t ReadingKind : " + get_reading_kind(data_block.Reading_Kind)
		print "\t NmeaGpggaLocation : " + data_block.NmeaGpggaLocation
		print "\t Data count : " + str(len(data_block.OutputDataPoints))	#note : data_block.OutputDataPoints is not the true decibel representation of the PSD data! Please see below.

		#Convert data points from Q format to IEEE754 floating point.
		#!!!!!slow part!!!!!
		db_data = data_to_float_decibel(data_block.OutputDataPoints)
		
		#plot the result (if requested).
		if plot_psd == cnt or plot_psd == 0:
			freq_mhz = np.linspace(data_block.StartFrequencyHz/1e6,data_block.StopFrequencyHz/1e6,num=len(data_block.OutputDataPoints))
			plt.plot(freq_mhz,db_data[0:])
			plt.xlabel('frequency (MHz)')
			plt.title('PSD plot. Timestamp:' + str(data_block.Time_stamp.value) + ', Type : ' + get_reading_kind(data_block.Reading_Kind))
			plt.ylabel('PSD (dBm/Bin if Calibrated Sensor, dBFS/Bin if Not Calibrated)')
			plt.show()

		#dump to a CSV file (if requested).
		if dump_csv == cnt or dump_csv == 0:
			f_write.write("Block," + str(cnt) + "\n")
			f_write.write("timestamp," + time.ctime(data_block.Time_stamp.value*time_scale  + time.altzone) + "\n")	#Python automatically adjusts the timezone, but that is not desirable. So, roll-back by adding back the time offset  "time.altzone". 
			f_write.write("Start Freq," + str((data_block.StartFrequencyHz)/1e6) + "Mhz" + "\n")
			f_write.write("Stop Freq," + str((data_block.StopFrequencyHz)/1e6) + "Mhz" + "\n")
			f_write.write("Data Type," + get_reading_kind(data_block.Reading_Kind) + "\n")
			f_write.write("NmeaGpggaLocation," + data_block.NmeaGpggaLocation + "\n")
			f_write.write("Data count," + str(len(data_block.OutputDataPoints)) + "\n")
			
			#dump the main IQ data
			f_write.write("------DATA STARTS HERE------ \n")
			f_write.write("\n".join(str(x) for x in db_data))				

			#add an extra line at the end of the block.
			f_write.write("\n")

		#dump to a mat file (if requested).
		if dump_mat == cnt or dump_mat == 0:
			sio.savemat(str(cnt)+'.mat',{'cnt':cnt,'timestamp':data_block.Time_stamp.value*time_scale  + time.altzone,'start_freq':data_block.StartFrequencyHz,'end_freq':data_block.StopFrequencyHz,'data_type':get_reading_kind(data_block.Reading_Kind), 'data':db_data})

		#update minimum frequency and the maximum frequency observed so far (if necessary).
		min_freq = min(min_freq, data_block.StartFrequencyHz)
		max_freq = max(max_freq, data_block.StopFrequencyHz)
		
		#increment the total data points encountered so far.
		data_cnt_sum = data_cnt_sum + len(data_block.OutputDataPoints)
	
	#For loop finished; print out the final summary.
	print "\n---------SUMMARY---------------\n"
	print "min starting freq : " +  str((min_freq)/1e6) + "Mhz"
	print "max stoping freq : " +  str((max_freq)/1e6) + "Mhz"
	print "Total Data points #: " + str(data_cnt_sum)
	print "Data point size (upper bound): " + str(data_cnt_sum * 3) + "Bytes (" + str((data_cnt_sum * 3)/(1024.0*1024)) + "MiB)"
	print "\n-------------------------------\n"

#--------------------------------------------------
# Main routine (int main() equivalent)
#--------------------------------------------------

#set argument parser
parser = argparse.ArgumentParser()
parser.add_argument("path", help="input file path")
parser.add_argument("-p", "--plot-psd", type=int, nargs='?', const=-1, help="Plot PSD Data at (PLOT_PSD)th block. Prints out every snapshots if setted zero.")
parser.add_argument("-d", "--dump-csv", type=int, nargs='?', const=-1, help="Dumps (DUMP_CSV)th data block to a CSV file. Name of the generated snapshot file is equal to the name of the input file with .csv appended at the end. Dumps out every snapshots if setted zero.")
parser.add_argument("-m", "--dump-mat", type=int, nargs='?', const=-1, help="Dumps (DUMP_CSV)th data block to a mat file. Dumps out every snapshots if setted zero.")
args=parser.parse_args()

#open file.
f = open(args.path,"rb");

#make a CSV file if necessary.
if args.dump_csv >= 0:
	f_write = open(args.path+".csv","w");
else:
	f_write = "";

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
print_file_summary(scan_file_read,args.plot_psd,args.dump_csv,args.dump_mat)

#close the csv dump file.
if args.dump_csv >= 0:
	f_write.close()
