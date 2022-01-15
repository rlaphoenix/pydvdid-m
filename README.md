# pydvdid-m

![downloads](https://pepy.tech/badge/pydvdid-m)
![license](https://img.shields.io/pypi/l/pydvdid-m.svg)
![wheel](https://img.shields.io/pypi/wheel/pydvdid-m.svg)
![versions](https://img.shields.io/pypi/pyversions/pydvdid-m.svg)

Pure Python implementation of the Windows API method `IDvdInfo2::GetDiscID`.  
This is a modification of [sjwood's pydvdid](https://github.com/sjwood/pydvdid).

The Windows API method `IDvdInfo2::GetDiscID` is used by Windows Media Center to compute a
'practically unique' 64-bit CRC for metadata retrieval. It's metadata retrieval API has
sadly since shutdown around October 2019 and all it's information is presumably lost.

