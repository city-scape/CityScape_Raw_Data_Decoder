#!/usr/bin/env python

#This script accepts an uncompressed Microsoft Spectrum Observatory PSD scan file, processes and displays summarized results.
#Note that spectrum observatory scan files are compressed in default. Decompress them with decompress.exe first (.NET / Mono executable).

#Usage : ./psdFile_process.py target_file (Unix with execute permission)
#         python psdFile_process.py target_file (Windows or with non-execute permission)
#Requirements: Python 2.7 with Protoc Python bindings (Ubuntu package name: python-protobuf). psdFile_pb2.py must be present in the same directory.

#See: https://developers.google.com/protocol-buffers/docs/pythontutorial
#(* This source code is heavily based on the example codes present on the above website.)
#Last-modified: Jul 5, 2016 (Kyeong Su Shin)

import sys
import psdFile_pb2
import os.path
import time
import matplotlib.pyplot as plt
import numpy as np

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
	if scale == psdFile_pb2.Timestamp.HOURS:	#Hours
		time_scale = 3600
	elif scale == psdFile_pb2.Timestamp.MINUTES: #Minutes
		time_scale = 60
	else:
		raise Exception('Unexpected timestamp scale.')		
		
	return time_scale
	
#Print out the "config" section of the data file and call "print_data_block_summary"
#to print out the summarized version of the data blocks.
#input: psdFile_pb2.ScanFile()
#output: none (directly prints out to stdout)
def print_file_summary(data):
	
	#Print out station configurations
	print "\n \n \n \n -----------------CONFIG BLOCK-----------------"
	#"replace" statements are not necessary, but they are used to re-format the "HardwareConfiguration" 
	#section of the config metadata (which has \\r, \\n, and \\t instead of their actual ASCII codes).
	print str(data.Config).replace("\\n","\n\t").replace("\\r","").replace("\\t","\t")
	print "---------------CONFIG BLOCK END---------------\n \n \n \n"

	#Print out summary of the data blocks.
	print "--------------DATA BLOCK SUMMARY--------------"
	print_data_block_summary(data)
	print "------------DATA BLOCK SUMMARY END------------ \n "

#Print out summary of the data blocks.
#input: psdFile_pb2.ScanFile()
#output: none (directly prints out to stdout)
def print_data_block_summary(data):
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
		
		#plot the result.
		#plt.plot(db_data[0:1023])
		#plt.show()

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

#if no argument passed, warn user.
if (len(sys.argv) <= 1):
		print "Usage : ", sys.argv[0], " target_file"
		sys.exit(1)

#if target file not found, warn user.
elif (os.path.exists(sys.argv[1]) == False):
		print "File not found!"
		sys.exit(2)

#open file.
f = open(sys.argv[1],"rb");

#read and close file.
scan_file_read = psdFile_pb2.ScanFile()
scan_file_read.ParseFromString(f.read())
f.close()

#process.
print_file_summary(scan_file_read)
