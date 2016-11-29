#!/usr/bin/env python

#This script accepts an uncompressed Microsoft Spectrum Observatory RAW IQ scan file, processes and displays summarized results.
#Note that spectrum observatory scan files are compressed in default. Decompress them with decompress.exe first (.NET / Mono executable).

#Usage : ./rawIQ_process.py target_file (Unix with execute permission)
#         python rawIQ_process.py target_file (Windows or with non-execute permission)
#Requirements: Python 2.7 with Protoc Python bindings (Ubuntu package name: python-protobuf). rawIQ_pb2.py must be present in the same directory.

#See: https://developers.google.com/protocol-buffers/docs/pythontutorial
#(* This source code is heavily based on the example codes present on the above website.)
#Last-modified: Jul 5, 2016 (Kyeong Su Shin)

import sys
import rawIQ_pb2
import os.path
import time
import matplotlib.pyplot as plt
import numpy as np

#Print out the "config" section of the data file and call "print_data_block_summary"
#to print out the summarized version of the RAW IQ snapshot blocks.
#input: rawIQ_pb2.RawIqFile()
#output: none (directly prints out to stdout)
def print_rawIQ_summary(rawIQ_read):

	#Print out station configurations
	print "\n \n \n \n -----------------CONFIG BLOCK-----------------"
	#"replace" statements are not necessary, but they are used to re-format the "HardwareConfiguration" 
	#section of the config metadata (which has \\r, \\n, and \\t instead of their actual ASCII codes).
	print str(rawIQ_read.Config).replace("\\n","\n\t").replace("\\r","").replace("\\t","\t")
	print "---------------CONFIG BLOCK END---------------\n \n \n \n"
	
	#Print out summary of the snapshot data blocks.
	print "--------------DATA BLOCK SUMMARY--------------"
	print_data_block_summary(rawIQ_read)
	print "------------DATA BLOCK SUMMARY END------------ \n "

#Print out summary of the data blocks.
#input: rawIQ_pb2.RawIqFile()
#output: none (directly prints out to stdout)
def print_data_block_summary(rawIQ_read):
	cnt = 0							#total data blocks within a file.
	data_cnt_sum = 0				#total data points within a file. (# blocks * data points per block)
	min_time = 9223372036854775807 #earliest timestamp observed. (initialized to int64_max)
	max_time = -1					#latest timestamp value observed.
	min_freq = float("inf")		#minimum snapshot starting frequency observed.
	max_freq = -1					#maximum snapshot stoping frequency observed.
	
	#for each block
	for data_block in rawIQ_read.SpectralIqData:
		#count up
		cnt = cnt + 1

		#print out block information
		#(comment out to reduce amount of information displayed.)
		print "Block " + str(cnt) + " : "
		print "\t timestamp : " + time.ctime(data_block.Time_stamp.value/10000000  + time.altzone)	#Python automatically adjusts the timezone, but that is not desirable. So, roll-back by adding back the time offset  "time.altzone". 
		print "\t Start Freq : " + str((data_block.StartFrequencyHz)/1e6) + "Mhz"
		print "\t Stop Freq : " + str((data_block.StopFrequencyHz)/1e6) + "Mhz"
		print "\t Center Freq : " + str((data_block.CenterFrequencyHz)/1e6) + "Mhz"
		print "\t NmeaGpggaLocation : " + data_block.NmeaGpggaLocation
		print "\t Data count : " + str(len(data_block.DataPoints))

		# plot raw
		#plt.plot(data_block.DataPoints)
		#plt.show()
		
		#update min/max timestamp, frequency values.
		min_time = min(min_time, data_block.Time_stamp.value)
		max_time = max(max_time, data_block.Time_stamp.value)
		min_freq = min(min_freq, data_block.StartFrequencyHz)
		max_freq = max(max_freq, data_block.StopFrequencyHz)
		
		#increment the total number of data points observed.
		data_cnt_sum = data_cnt_sum + len(data_block.DataPoints)
	
	#Done with the loop; now print out the overall summary.
	print "\n---------SUMMARY---------------\n"
	print "min_time : " + time.ctime(min_time/10000000 + time.altzone) 
	print "max_time : " + time.ctime(max_time/10000000  + time.altzone) 
	print "min starting freq : " +  str((min_freq)/1e6) + "Mhz"
	print "max stoping freq : " +  str((max_freq)/1e6) + "Mhz"
	print "Total IQ Data points #: " + str(data_cnt_sum)
	print "Total IQ Data points (in bytes): " + str(data_cnt_sum * 8) + "Bytes (" + str((data_cnt_sum * 8)/(1024.0*1024)) + "MiB)"
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
rawIQ_read = rawIQ_pb2.RawIqFile()
rawIQ_read.ParseFromString(f.read())
f.close()

#process.
print_rawIQ_summary(rawIQ_read)
