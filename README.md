
decompress.exe : Decompresses dsox or dsor files into a uncompressed Protobuffer files. Requires .NET runtime. On Linux, mono tool can be used to run this.  
decompress.cs : source code of decompress.exe above. On Linux, mcs tool can be used to compile into the executable format.  
protobuf-windows-build(full).zip: protobuf binary, with max file size = 512M, for Windows 7 or higher.  
protoc.exe : protobuffer compiler (for Windows). Can be used to decode a protobuffer database file and generate a human-readable text file. Max file size = 512MB.  
psdFile.proto : protobuf definition file for PSD files ("aggregate" files). Defines file structure of MS Spectrum Observatory PSD scan files. Can be used along with protobuf libraries to encode or decode MS Spectrum Observatory PSD files.  
rawIQ.proto : protobuf definition file for RAW IQ files. Defines the file structure of MS Spectrum Observatory RAW IQ files. Can be used along with protobuf libraries to encode or decode MS Spectrum Observatory RAW IQ files.  

Sample Outputs/aggregate.zip : Sample output of a processed PSD ("aggregate") file (in ASCII text).  
Sample Outputs/RAW_IQ.zip : Sample output of a processed RAW IQ file (in ASCII text).  
	
python/psdFile_pb2.py : python protobuf "data access code" for PSD scan files. (=Python PSD scan definition file,  auto-generated from psdFile.proto file above.)  
python/rawIQ_pb2.py : python protobuf "data access code" for RAW IQ files. (=Python RAW IQ definition file,  auto-generated from rawIQ.proto file above.)  
python/psdFile_process.py : python code to read and process uncompressed PSD scan files.  
python/rawIQ_process.py : python code to read and process uncompressed RAW IQ files.  
	
Decompress(uncompress) dsor or dsox files into an uncompressed protobuf file:  
Windows with .NET runtime:  

	decompress.exe source_path output_path  
	
or, if Unix-like OS with a Mono runtime:  

	mono decompress.exe source_path output_path  

An uncompressed protobuf file to a human-readable text file, using protoc:  
Command to convert RAW IQ files (assuming that rawIQ.proto file is located in current directory. Also assuming UNIX Shell syntax):  

	protoc -I=./ --decode=MSSO_RawIQ.RawIqFile ./rawIQ.proto < input_path > output_path  

Command to convert PSD files (same assumptions as above):  

	protoc -I=./ --decode=MSSO_PSD.ScanFile ./psdFile.proto < input_path > output_path  
		  
*"protoc" must be installed. (see below for "protoc" installation.)  
  
Using Python to directly process RAW IQ or PSD scan files:  
-System requirement : Python 2.7 with Protobuf Python bindings, matplotlib.pyplot. (Ubuntu package : python-protobuf)  
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
