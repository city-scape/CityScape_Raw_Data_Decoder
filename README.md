## Quick Start

1.Make sure that the dependencies are met. Dependencies:

	-Python 2.7 
	
	-Protobuf Python binding (python-protobuf)
	
	-MatPlotLib
	
	-NumPy
	
	-SciPy

2.Download the files ("python" directory).

3.Launch a terminal (command prompt), and cd to the python directory.

4.To dump data into Matlab-supported format (.mat), run (from where the downloaded Python files are located):

	python rawIQ_process.py -m0 extracted_file_path 
	
(for Raw I-Q data), or 

	python psdFile_process.py -m0 extracted_file_path
	
(for PSD data). 

Note that this may take up to several minutes (for large files).

This will convert the extracted data into Matlab-decodable (.mat) format. There are other options as well: you can type 'python rawIQ_process.py --help' or 'python psdFile_process.py --help' to see list of available options.

## List of Files
decompress.exe : Decompresses dsox or dsor files into uncompressed Protobuffer files. Requires .NET or Mono runtime.

decompress.cs : source code of decompress.exe. 

decompress.py : Python equivalent of decompress.exe (if you prefer Python).

protobuf-windows-build(full).zip: protobuf binary, with max file size = 512M, for Windows 7 or higher.  

protoc.exe : protobuffer compiler (for Windows). Can be used to decode a protobuffer database file and generate a human-readable text file. Max file size = 512MB (Use Python based parser for larger files).

psdFile.proto : Protobuf definition file for the aggregated PSD files (used by the CityScape project). Protobuf libraries and binaries need this file to correctly decode (or encode) the downloaded PSD files.

rawIQ.proto : psdFile.proto : Protobuf definition file for the Raw I-Q files (used by the CityScape project). Protobuf libraries and binaries need this file to correctly decode (or encode) the downloaded files.
	
python/psdFile_pb2.py : Protobuf "data access code" for PSD scan file, for Python 2.7. Required to encode or decode CityScape PSD data files with Python; can be generated from psdFile.proto if necessary. 

python/rawIQ_pb2.py : Protobuf "data access code" for RAW IQ file, for Python 2.7. Required to encode or decode CityScape I-Q data files with Python; can be generated from psdFile.proto if necessary. 

python/psdFile_process.py : A sample Python program to read and process uncompressed PSD scan files. Provides a simple CLI interface to plot or dump the data.

python/rawIQ_process.py : A sample Python program to read and process uncompressed RAW IQ files.  Provides a simple CLI interface to plot or dump the data.

## Usage
### Decompressing Files (Optional if using Python-based Parser)

Decompress(uncompress) dsor or dsox files into an uncompressed Protobuf files:  

Windows with .NET runtime:  

	decompress.exe source_path output_path  
	
Mono runtime:  

	mono decompress.exe source_path output_path  

### Parsing, with "protoc"
An uncompressed protobuf file to a human-readable text file, using protoc:  
Command to convert RAW IQ files (assuming that rawIQ.proto file is located in current directory. Also assuming UNIX-like Shell style syntax):  

	protoc -I=./ --decode=MSSO_RawIQ.RawIqFile ./rawIQ.proto < input_path > output_path 

Command to convert PSD files (same assumptions as above):  

	protoc -I=./ --decode=MSSO_PSD.ScanFile ./psdFile.proto < input_path > output_path  
		  
*"protoc" must be installed. (see below for "protoc" installation.)  
*May not be able to process large files (protoc may reject files larger than 64MBytes).

### Decoding, with Python-based Parser (Recommended)

Dependency : 

	-Python 2.7 
	
	-Protobuf Python binding (python-protobuf)
	
	-MatPlotLib
	
	-NumPy
	
	-SciPy

example, for extracting data into matlab (mat) files:   

	python/rawIQ_process.py -m0 RAW_IQ.bin		#Process the uncompressed file. Dump all data into Matlab (.mat) files.

To see list other optional arguments, run:

	python/rawIQ_process.py --help
	
or

	python/psdFile_process.py  --help

*Maximum processible file size does not apply to the Python-based parser (Only applies to protoc). 

## Misc.

### Protobuf Installation
GitHub URL for protobuf: https://github.com/google/protobuf . Download the project. Update CodedInputStream::SetTotalBytesLimit() of google/protobuf/io/coded_stream.h appropriately to adjust the maximum allowable input file size (our RAW IQ files and PSD files can grow much larger than the typical value - 512MB or 1GB would be a good estimate) and build the project.  
	
If you are using Windows 7 or higher, or using GNU/Linux with Wine installed, you can use the protobuf build uploaded. Max input file size for protoc: 512Mbyte.  
  
In Debian-based Linux distros, you can simply download protobuf by running sudo apt-get protobuf-compiler. However, the maximum input file size for this protoc build can be smaller than what you want. You can still use the Python-based parser, as that limit does not apply to the Python-base parser.
  
### Understanding CityScape PSD / RAW IQ File Data Structure
-*.proto files serve as documentation of the RAW IQ / PSD protobuf file structures. We recommend reading those files in order to understand what kind of metadata can be stored in these data files.  
  
-To convert a timestamp with "scale: TICKS" into a UNIX timestamp, simply divide it by 10000000. (Note that this is a special case. The timestamp stored in protobuf-net format is already adjusted to start at 1970/01/01 00:00AM.)  
  
-Power in the PSD files are represented in a fixed-point format ( https://en.wikipedia.org/wiki/Q_(number_format) ), which are then stored as signed int16 numbers. 

### Units of the I-Q Data and PSD Estimates
-If your station is amplitude-calibrated, generated I-Q Data are normalized in a such way that the periodogram of the I-Q data will generate power spectral densitiy estimates in a dBm scale (instead of in arbitrary scale). This is done by applying a software-level amplification (or attenuation) to the received I-Q data. If the station is not calibrated, it will generate data in an arbitrary scale.

Currently (May 10, 2017), every station hosted at cityscape.cloudapp.net are amplitude-calibrated.

-Similarly, PSD estimate data are in dBm/(FFT Bin Size) if the station is amplitude-calibrated. If not, it is in an arbitrary scale.

### Troubleshoot

**Exception thrown by the Python script:**

-Supplied *_pb2.py files may not work correctly with some versions of Python-Protobuf library. You can re-build *_pb2.py files with your own Protobuf library. Alternatively, you can try different versions of Python-Protobuf library. *_pb2.py rebuild Guide : https://developers.google.com/protocol-buffers/docs/pythontutorial .

**Decompress.exe won't run:**

-Try installing recent version of .NET Framework (Windows) or Mono (Linux).

**Decoded data look incorrect.**

-Check if you used the correct parser script - psdFile_process.py for aggregated PSD files, rawIQ_process.py for raw I-Q data files.

-If you suspect that the data generated from the station is incorrect (=fault of the station, not the parser), try contacting the station administrator.


**It takes very long (several minutes) to parse data.**

Yes.
