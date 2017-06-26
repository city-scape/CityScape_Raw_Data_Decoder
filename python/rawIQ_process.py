#!/usr/bin/env python

#This script accepts a Microsoft Spectrum Observatory RAW IQ scan file, processes and displays summarized results.

#Usage : ./rawIQ_process.py target_file (Unix with execute permission)
#         python rawIQ_process.py target_file (Windows or with non-execute permission)
#Requirements: Python 2.7 with Protoc Python bindings (Ubuntu package name: python-protobuf). rawIQ_pb2.py must be present in the same directory.

#See: https://developers.google.com/protocol-buffers/docs/pythontutorial

#Last-modified: Mar 25, 2017 (Kyeong Su Shin)
#TODO : refactoring (getting quite dirty..)

import sys
import argparse
import rawIQ_pb2
import os.path
import time
import matplotlib.pyplot as plt
import numpy as np
import scipy.io as sio
import zlib

from scipy import signal
from operator import add

#Decompress (before parsing)
def decompress (dat):
	return zlib.decompress(dat,-15)

#Print out the "config" section of the data file and call "print_data_block_summary"
#to print out the summarized version of the RAW IQ snapshot blocks.
#input: rawIQ_pb2.RawIqFile()
#output: none (directly prints out to stdout)
def print_rawIQ_summary(rawIQ_read,raw_plot,psd_plot,dump_csv,f_write_csv,dump_mat,f_write_cfile,dump_cfile):

	#Print out station configurations
	print "\n \n \n \n -----------------CONFIG BLOCK-----------------"
	#"replace" statements are not necessary, but they are used to re-format the "HardwareConfiguration" 
	#section of the config metadata (which has \\r, \\n, and \\t instead of their actual ASCII codes).
	print str(rawIQ_read.Config).replace("\\n","\n\t").replace("\\r","").replace("\\t","\t")
	print "---------------CONFIG BLOCK END---------------\n \n \n \n"
	
	#Print out summary of the snapshot data blocks.
	print "--------------DATA BLOCK SUMMARY--------------"
	print_data_block_summary(rawIQ_read,raw_plot,psd_plot,dump_csv,f_write_csv,dump_mat,f_write_cfile,dump_cfile)
	print "------------DATA BLOCK SUMMARY END------------ \n "

#Print out summary of the data blocks.
#input: rawIQ_pb2.RawIqFile()
#output: none (directly prints out to stdout)
def print_data_block_summary(rawIQ_read,raw_plot,psd_plot,dump_csv,f_write_csv,dump_mat,f_write_cfile,dump_cfile):
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
		print "\t Start Freq : " + str((data_block.StartFrequencyHz)/1e6) + "MHz"
		print "\t Stop Freq : " + str((data_block.StopFrequencyHz)/1e6) + "MHz"
		print "\t Center Freq : " + str((data_block.CenterFrequencyHz)/1e6) + "MHz"
		print "\t NmeaGpggaLocation : " + data_block.NmeaGpggaLocation
		print "\t Data count : " + str(len(data_block.DataPoints)/2)

		data_block_i = data_block.DataPoints[::2]
		data_block_q = [x*1j for x in data_block.DataPoints[1::2]]		
		data_block_complex = map(add, data_block_i, data_block_q)
		
		#plot RAW IQ
		if raw_plot == cnt or raw_plot == 0:
			#i component
			plt.plot(np.real(data_block_complex),'b')
			#q component
			plt.plot(np.imag(data_block_complex),'r')
			plt.ylabel('Amplitude')
			plt.title('RAW IQ data plot. Freq:' + str((data_block.CenterFrequencyHz)/1e6) + "MHz" + ', Timestamp:' + str(data_block.Time_stamp.value))
			#plot
			plt.show()		

		#plot PSD
		if psd_plot == cnt  or psd_plot == 0:
			#determine psd
			#http://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.periodogram.html
			f, psd = signal.periodogram(data_block_complex,(data_block.StopFrequencyHz - data_block.StartFrequencyHz))
			
			#calculate dB
			psd_bel = np.log10(psd)
			psd_decibel = [x * 10 for x in psd_bel]

			#frequency calculation
			f_offsetted = [(x + data_block.CenterFrequencyHz)/(1e6) for x in f]

			#plot
			plt.plot(f_offsetted[1:], psd_decibel[1:])
			plt.ylim(ymax = 0, ymin = -175)
			plt.xlabel('frequency (MHz)')
			plt.title('RAW IQ data PSD plot. Freq:' + str((data_block.CenterFrequencyHz)/1e6) + "MHz" + ', Timestamp:' + str(data_block.Time_stamp.value))
			plt.ylabel('PSD (dBm/Bin if Calibrated Sensor, dBFS/Bin if not)')
			plt.show()
		
		#dump to CSV
		if dump_csv == cnt or dump_csv == 0:
			#dump metadata of the snapshot
			f_write_csv.write("Block," + str(cnt) + "\n")
			f_write_csv.write("timestamp," + time.ctime(data_block.Time_stamp.value/10000000  + time.altzone) + "\n")	#Python automatically adjusts the timezone, but that is not desirable. So, roll-back by adding back the time offset  "time.altzone". 
			f_write_csv.write("Start Freq," + str((data_block.StartFrequencyHz)/1e6) + "MHz" + "\n")
			f_write_csv.write("Stop Freq," + str((data_block.StopFrequencyHz)/1e6) + "MHz" + "\n")
			f_write_csv.write("Center Freq," + str((data_block.CenterFrequencyHz)/1e6) + "MHz" + "\n")
			f_write_csv.write("NmeaGpggaLocation," + data_block.NmeaGpggaLocation + "\n")
			f_write_csv.write("Data count," + str(len(data_block.DataPoints)/2) + "\n")
			
			#dump the main IQ data
			#TODO : moar efficient implementation wanted.
			#f_write.write("------DATA STARTS HERE------ \n")
			#f_write.write("\n".join(str(x) for x in data_block_complex))				
			f_write_csv.write("I,Q \n")
			re = np.real(data_block_complex)
			im = np.imag(data_block_complex)
			for i in xrange(0,len(data_block.DataPoints)/2):
				f_write_csv.write(str(re[i])+","+str(im[i])+"\n")

			#add an extra line at the end of the block.
			f_write_csv.write("\n")

		#f_write_cfile,dump_cfile
		#dump to cfile
		if dump_cfile == cnt or dump_cfile == 0:
			data_754single = np.array(data_block.DataPoints).astype(np.dtype(np.float32))
			data_754single.tofile(f_write_cfile,"",)
		#dump to mat
		if dump_mat == cnt or dump_mat == 0:
			sio.savemat(str(cnt)+'.mat',{'cnt':cnt,'timestamp':data_block.Time_stamp.value/10000000  + time.altzone,'freq':data_block.CenterFrequencyHz,'data':data_block_complex})
	
		#update min/max timestamp, frequency values.
		min_time = min(min_time, data_block.Time_stamp.value)
		max_time = max(max_time, data_block.Time_stamp.value)
		min_freq = min(min_freq, data_block.StartFrequencyHz)
		max_freq = max(max_freq, data_block.StopFrequencyHz)
		
		#increment the total number of data points observed.
		data_cnt_sum = data_cnt_sum + (len(data_block.DataPoints)/2)
	
	#Done with the loop; now print out the overall summary.
	print "\n---------SUMMARY---------------\n"
	print "min_time : " + time.ctime(min_time/10000000 + time.altzone) 
	print "max_time : " + time.ctime(max_time/10000000  + time.altzone) 
	print "min starting freq : " +  str((min_freq)/1e6) + "MHz"
	print "max stoping freq : " +  str((max_freq)/1e6) + "MHz"
	print "Total IQ Data points #: " + str(data_cnt_sum)
	print "Total IQ Data points (in bytes): " + str(data_cnt_sum * 8 *2) + "Bytes (" + str((data_cnt_sum * 8 *2)/(1024.0*1024)) + "MiB)"
	print "\n-------------------------------\n"

#--------------------------------------------------
# Main routine (int main() equivalent)
#--------------------------------------------------

#set argument parser
parser = argparse.ArgumentParser()
parser.add_argument("path", help="input file path")
parser.add_argument("-r", "--plot-raw", type=int, nargs='?', const=-1, help="Plot RAW IQ Data at (PLOT_RAW)th snapshot. Prints out every snapshots if setted zero.")
parser.add_argument("-p", "--plot-psd", type=int, nargs='?', const=-1, help="Plot PSD Data at (PLOT_PSD)th snapshot. Prints out every snapshots if setted zero.")
parser.add_argument("-d", "--dump-csv", type=int, nargs='?', const=-1, help="Dumps (DUMP_CSV)th snapshot data to a CSV file. Name of the generated snapshot file is equal to the name of the input file with .csv appended at the end. Dumps out every snapshots if setted zero.")
parser.add_argument("-m", "--dump-mat", type=int, nargs='?', const=-1, help="Dumps (DUMP_MAT)th snapshot data to a mat file. Dumps out every snapshots if setted zero.")
parser.add_argument("-g", "--dump-cfile", type=int, nargs='?', const=-1, help="Dumps (DUMP_CFILE)th snapshot data to a GNURadio-compatible cfile. Aggregates and dumps out every snapshots if setted zero.")

args=parser.parse_args()

#open file.
f = open(args.path,"rb");


#make a CSV file if necessary.
if args.dump_csv >= 0:
	f_write_csv = open(args.path+".csv","w");
else:
	f_write_csv = "";

#make a cfile if necessary.
if args.dump_cfile >= 0:
	f_write_cfile = open(args.path+".cfile","wb");
else:
	f_write_cfile = "";

#Attempt decompression. If fails, assume decompressed data and just push that into the Protobuf decoder.
f_str = f.read()
f.close()
try:
	decompress_out = decompress (f_str)
	f_str = decompress_out
except Exception:
	pass


#read and close file.
rawIQ_read = rawIQ_pb2.RawIqFile()
rawIQ_read.ParseFromString(f_str)

#process.
print_rawIQ_summary(rawIQ_read,args.plot_raw,args.plot_psd,args.dump_csv,f_write_csv,args.dump_mat,f_write_cfile,args.dump_cfile)

#close the dump file.
if args.dump_csv >= 0:
	f_write_csv.close()
if args.dump_cfile >= 0:
	f_write_cfile.close()
