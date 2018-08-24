# ntdiff

A little dirty scripting machinery for http://ntdiff.github.io - just in case anyone would want to fork it or make it somehow
better. Note that I've decided to not include DLLs/PDBs/EXEs for obvious reasons - with a bit of work, you can obtain
them on your own. SHA256 hashes of each file is provided here for convenience: [Bin/sha256sum.txt](Bin/sha256sum.txt).
PDBs are actually downloaded by **symchk.exe**, which can be found in WDK - look into [Tools](Tools) folder for more
information.
