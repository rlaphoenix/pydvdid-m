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

## Changes compared to sjwood's repo

1. License changed from Apache-2.0 to GPL-3.0.
2. Moved build tools and dependency management from setuptools and requirements.txt to poetry.
3. Support for Python 2.x and Python <3.6 has been dropped. 
4. All tests were removed entirely simply because a lot of the tests would need to be refactored
   for general code changes, and some tests might not be needed anymore.
5. All custom exceptions were removed entirely and replaced with built-in ones.
6. CRC-64 related code were refactored and merged as one CRC64 class in one file.
7. The merged CRC64 class contains various improvements over the original code, including
   improvements with doc-strings, formatting, and such.
8. Various BASH shell scripts and config files were removed entirely as they are deemed unnecessary.

Other than that, the rest of the changes are general code improvements in various ways.
There may be more differences as the repo gets commits, but these are the primary differences from
sjwoods' commit https://github.com/sjwood/pydvdid/commit/03914fb7e24283c445e5af724f9d919b23caaf95 to
the beginnings of this repository.
