## Quick Start
First option is to make a parser out of the original station source code ( https://spectrumobservatory.codeplex.com/SourceControl/latest#Integration-branch/external/dev/Common/MS.IO.RawIqFile/RawIqFileReader.cs ). I personally have not tried this method.

Second option is to use a Python based parser (*no GUI; command line tool) which I wrote. It is slow, but it gets the job done. It is available at: https://github.com/city-scape/CityScape_Raw_Data_Decoder .

A quick guide (second option):

1.Make sure that the dependencies are met. Dependencies:

-.NET Framework or a compatible runtime (tested with Mono 4.2.1)
-Python 2.7
-Python-Protobuf (tested with v.2.6.1 – 3.0.0)
-MatPlotLib
-NumPy
-SciPy

2.Download the files (decompress.exe and "python" directory of https://github.com/city-scape/CityScape_Raw_Data_Decoder ).

3.Launch a terminal (command prompt) on where the downloaded files are located. run:

'decompress.exe data_file_path output_file_path' (Windows + .Net runtime) or 'mono decompress.exe data_file_path output_file_path' (Linux + Mono runtime). This will decompress the data file (but will not convert them to Matlab-supported format yet).

4.Then, from where the downloaded Python files are located, run:

python rawIQ_process.py -m0 extracted_file_path (for Raw I-Q data) or python psdFile_process.py -m0 extracted_file_path (for PSD data). Note that this may take up to several minutes (for large files).

This will convert the extracted data into Matlab-decodable (.mat) format. There are other options as well: you can type 'python rawIQ_process.py --help' or 'python psdFile_process.py --help' to see list of options available.


Troubleshoot:
Exception thrown by the Python script:
-May not work correctly with some older versions of Python-Protobuf library. You may have to re-build *_pb2.py files using protoc or update your Python-Protobuf version. Guide : https://developers.google.com/protocol-buffers/docs/pythontutorial .
-Make sure you input extracted file (by decompress.exe) to the Python script, not the compressed file.

Decompress.exe won't run:
-Try installing recent version of .NET Framework (Windows) or Mono (Linux).

## List of Files
decompress.exe : Decompresses dsox or dsor files into uncompressed Protobuffer files. Requires .NET or Mono runtime.
decompress.cs : source code of decompress.exe. 
protobuf-windows-build(full).zip: protobuf binary, with max file size = 512M, for Windows 7 or higher.  
protoc.exe : protobuffer compiler (for Windows). Can be used to decode a protobuffer database file and generate a human-readable text file. Max file size = 512MB (Use Python based parser for larger files).
psdFile.proto : Protobuf definition file for the aggregated PSD files (used by the CityScape project). Protobuf libraries and binaries need this file to correctly decode (or encode) the downloaded PSD files.

rawIQ.proto : psdFile.proto : Protobuf definition file for the Raw I-Q files (used by the CityScape project). Protobuf libraries and binaries need this file to correctly decode (or encode) the downloaded files.
	
python/psdFile_pb2.py : Protobuf "data access code" for PSD scan file, for Python 2.7. Required to encode or decode CityScape PSD data files with Python; can be generated from psdFile.proto if necessary. 
python/rawIQ_pb2.py : Protobuf "data access code" for RAW IQ file, for Python 2.7. Required to encode or decode CityScape I-Q data files with Python; can be generated from psdFile.proto if necessary. 
python/psdFile_process.py : A sample Python program to read and process uncompressed PSD scan files. Provides a simple CLI interface to plot or dump the data.
python/rawIQ_process.py : A sample Python program to read and process uncompressed RAW IQ files.  Provides a simple CLI interface to plot or dump the data.

## Usage
### Decompressing Files

You need to decompress the downloaded dsor or dsox files before processing them with Protobuf.

Decompress(uncompress) dsor or dsox files into an uncompressed Protobuf files:  

Windows with .NET runtime:  

	decompress.exe source_path output_path  
	
Mono runtime:  

	mono decompress.exe source_path output_path  

### Decoding, with "protoc"
An uncompressed protobuf file to a human-readable text file, using protoc:  
Command to convert RAW IQ files (assuming that rawIQ.proto file is located in current directory. Also assuming UNIX Shell syntax):  

	protoc -I=./ --decode=MSSO_RawIQ.RawIqFile ./rawIQ.proto < input_path > output_path  

Command to convert PSD files (same assumptions as above):  

	protoc -I=./ --decode=MSSO_PSD.ScanFile ./psdFile.proto < input_path > output_path  
		  
*"protoc" must be installed. (see below for "protoc" installation.)  
  
Using Python to directly process RAW IQ or PSD scan files:  

Dependency : 

	-Python 2.7 
	
	-Protobuf Python binding (python-protobuf)
	
	-MatPlotLib
	
	-NumPy
	
	-SciPy

-uncompress dsor or dsox files into uncompressed protobuf files, and then pass them into the Python scripts ("rawIQ_process.py or psdFile_process.py").  
ex:  

	mono decompress.exe RAW_IQ.bin.dsor RAW_IQ.bin	#uncompress the Protobuf file.  

	python/rawIQ_process.py RAW_IQ.bin					#process the uncompressed file.  
	
*You do NOT need to worry about the max file size when using Python, assuming that your machine has sufficient RAM. (It does use significant amount of RAM.)  

Libprotobuf (and protoc) installation:  
GitHub URL for protobuf: https://github.com/google/protobuf . Download the project. Update CodedInputStream::SetTotalBytesLimit() of google/protobuf/io/coded_stream.h appropriately to adjust the maximum allowable input file size (our RAW IQ files and PSD files can grow much larger than a typical protobuf file size limitation) and build the project.  
	
If you are using Windows 7 or higher, or using GNU/Linux with Wine installed, you can use the protobuf build uploaded. Max input file size for protoc: 512Mbyte.  
  
In Linux, you can simply download protobuf by running sudo apt-get protobuf-compiler. However, the maximum input file size for this protoc build is 64Mbyte. (Python scripts will work properly)  
  
Miscellaneous Notes:  
-*.proto file also serves as a documentation of the RAW IQ / PSD protobuf file structures. We recommend reading those files to understand what kind of metadata can be stored into the files.  
  
-To convert a timestamp with "scale: TICKS" into a UNIX timestamp, one can simply divide it by 10000000. (Note that this is a special case. The timestamp stored in protobuf-net format is already adjusted to start at 1970/01/01 00:00AM.)  
  
-Power in the PSD files are represented in a fixed-point format, which are then stored as signed int16 numbers. However, each point apparantly takes about 3 bytes. (This is probably because protobuf only supports 32bit / 64bit integers natively, but uses "Base 128 Variants" to compress smaller numbers. Please read: https://developers.google.com/protocol-buffers/docs/encoding#varints)  
