# pydvdid-m

![downloads](https://pepy.tech/badge/pydvdid-m)
![license](https://img.shields.io/pypi/l/pydvdid-m.svg)
![wheel](https://img.shields.io/pypi/wheel/pydvdid-m.svg)
![versions](https://img.shields.io/pypi/pyversions/pydvdid-m.svg)

Pure Python implementation of the Windows API method [IDvdInfo2::GetDiscID].  
This is a modification of [sjwood's pydvdid](https://github.com/sjwood/pydvdid).

The Windows API method [IDvdInfo2::GetDiscID] is used by Windows Media Center to compute a
'practically unique' 64-bit CRC for metadata retrieval. It's metadata retrieval API has
sadly since shutdown around October 2019 and all it's information is presumably lost.

  [IDvdInfo2::GetDiscID]: <https://docs.microsoft.com/en-us/windows/win32/api/strmif/nf-strmif-idvdinfo2-getdiscid>

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
9. Uses pycdlib to read from ISO and direct disc drives, instead of assuming that it's a folder.

Other than that, the rest of the changes are general code improvements in various ways.
There may be more differences as the repo gets commits, but these are the primary differences from
[sjwood's commit](https://github.com/sjwood/pydvdid/commit/03914fb7e24283c445e5af724f9d919b23caaf95) to
the beginnings of this repository.

## Important Information on DVD ID Accuracy

1. The DVD ID generated assumes that the input Disc, ISO, or VIDEO_TS folder has the original untouched
   file timestamps, file names, and header data. Any change or missing file will result in a different DVD ID.
2. Because of this, AnyDVD HD, DVDFab Passkey, or anything similar that may change the disc data at a
   driver-level should be disabled before the use of pydvdid-m.
3. Just because it is an ISO file, does not mean it is truly untouched in the header areas that matter.
   AnyDVD HD (and maybe others) may alter some bytes here and there when removing protection.
4. VIDEO_TS folders are typically created by extracting the data from an ISO or Disc, which will most likely
   re-generate file creation and modified timestamps. If you want truly accurate DVD IDs, I cannot advise
   the use of this project on VIDEO_TS folders.

If you want truly accurate DVD IDs, then only use this project direct from discs with all DVD ripping software
disabled and closed. Make sure nothing like AnyDVD HD or DVDFab Passkey is running in the background.

## Installation

```shell
$ pip install pydvdid-m
```

## Usage

You can run DvdId on all types of DVD video file structures:

- Direct from Disc, e.g., `/dev/sr0`, `\\.\E:`, or such.
- An ISO file, e.g., `/mnt/cdrom`, `C:/Users/John/Videos/FAMILY_GUY_VOLUME_11_DISC_1.ISO`.
- A VIDEO_TS folder*, `C:/Users/John/Videos/THE_IT_CROWD_D1/`.

Note: Generating a DVD ID from a VIDEO_TS folder has a high chance of providing an
invalid DVD ID. The algorithm uses file creation timestamps, and extracting VIDEO_TS folders
direct from Disc or from an ISO will most likely change them, especially when transferred or moved.

### CLI

```shell
phoenix@home@~$ dvdid "FAMILY_GUY_VOLUME_11_DISC_1.ISO"
<Disc>
<Name>FAMILY_GUY_VOLUME_11_DISC_1</Name>
<ID>db3804e3|1645f594</ID>
</Disc>
```

You can provide a path to an ISO file, or a mounted device, e.g.:

```shell
phoenix@home@~$ dvdid "/dev/sr0"
<Disc>
<Name>BBCDVD3508</Name>
<ID>3f041dfc|27ffd3a8</ID>
</Disc>
```

or on Windows via Raw Mounted Device:

```shell
PS> dvdid "\\.\E:"
<Disc>
<Name>BBCDVD3508</Name>
<ID>3f041dfc|27ffd3a8</ID>
</Disc>
```

### Package

You can also use pydvdid-m in your own Python code by importing it.  
Here's a couple of things you can do, and remember, you can use both ISO paths and mounted device targets.

```python
>>> from pydvdid_m import DvdId
>>> dvd_id = DvdId(r"C:\Users\John\Videos\FAMILY_GUY_VOLUME_11_DISC_1.ISO")
>>> dvd_id.disc_label
'BBCDVD3508'
>>> repr(dvd_id.checksum)
'<CRC64 polynomial=0x92c64265d32139a4 xor=0xffffffffffffffff checksum=0x3f041dfc27ffd3a8>'
>>> dvd_id.checksum
'3f041dfc|27ffd3a8'
>>> dvd_id.checksum.as_bytes
b"?\x04\x1d\xfc'\xff\xd3\xa8"
>>> dvd_id.dumps()
'<Disc>\n<Name>BBCDVD3508</Name>\n<ID>3f041dfc|27ffd3a8</ID>\n</Disc>'
```

## License

[GNU General Public License, Version 3](https://raw.githubusercontent.com/rlaphoenix/pydvdid-m/master/LICENSE)
