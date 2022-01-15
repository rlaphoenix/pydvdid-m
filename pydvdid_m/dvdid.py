from datetime import datetime
from inspect import cleandoc
from io import BytesIO
from pathlib import Path
from struct import pack_into
from typing import Union, Iterator, Optional

from dateutil.tz import tzoffset
from pycdlib import PyCdlib
from pycdlib.dr import DirectoryRecord
from pycdlib.pycdlibexception import PyCdlibInvalidInput

from pydvdid_m.crc64 import CRC64


class DvdId:
    def __init__(self, target: Union[str, PyCdlib]):
        """
        Computes a Windows API IDvdInfo2::GetDiscID-compatible 64-bit Cyclic Redundancy Check
        checksum from the DVD .vob, .ifo, and .bup files found in the supplied DVD device.
        """
        if isinstance(target, str):
            target = Path(target)
            if target.is_dir():
                raise NotImplementedError("Extracted VIDEO_TS folders are not yet supported.")
            else:
                # assume path to an ISO
                self.device = PyCdlib()
                self.device.open(str(target))
        elif isinstance(target, PyCdlib):
            self.device = target
        else:
            raise ValueError(f"Unsupported target: {target}")

        if not any(self._get_files("/VIDEO_TS")):
            # Not a DVD-Video Disc?
            raise FileNotFoundError(f"The /VIDEO_TS directory and it's files doesn't exist in {target}")

        # the polynomial used for this CRC-64 checksum is:
        # x^63 + x^60 + x^57 + x^55 + x^54 + x^50 + x^49 + x^46 + x^41 + x^38 + x^37 + x^34 + x^32 +
        # x^31 + x^30 + x^28 + x^25 + x^24 + x^21 + x^16 + x^13 + x^12 + x^11 + x^08 + x^07 + x^05 + x^2
        crc = CRC64(0x92c64265d32139a4)

        for file in self._get_files("/VIDEO_TS"):
            crc.update(self._get_dr_creation_time(file))
            crc.update(self._get_dr_size(file))
            crc.update(self._get_dr_name(file))

        for file in self._get_files("/VIDEO_TS"):
            if self._get_dr_name(file, as_string=True).upper() in ("VIDEO_TS.IFO", "VTS_01_0.IFO"):
                crc.update(self._get_first_64k_content(file))

        self.checksum = crc

    @property
    def disc_label(self) -> Optional[str]:
        """Get Disc Label. Returns the directory Name if not an ISO or Device."""
        if isinstance(self.device, PyCdlib):
            return self.device.pvd.volume_identifier.replace(b"\x00", b"").strip().decode()
        elif isinstance(self.device, Path):
            return self.device.name
        else:
            return None

    def dumps(self) -> str:
        """Return DVD ID with Disc Label in XML format."""
        xml = cleandoc("""
        <Disc>
        <Name>%s</Name>
        <ID>%s</ID>
        </Disc>
        """)
        if self.disc_label:
            if not isinstance(self.disc_label, str):
                raise ValueError("disc_label must be a string")
        xml = xml % (self.disc_label or "", str(self.checksum))
        return xml

    def dump(self, to: Union[Path, str]) -> int:
        """
        Save DVD ID with Disc Label in XML format.

        Path can be to a direct file path or directory path.
        A custom filename using the Disc Label will be used for you
        if it's a path to a directory or non-XML file.
        """
        if not to:
            raise ValueError("A save path must be provided.")
        if not isinstance(to, Path):
            to = Path(to)
        if to.is_dir():
            to = to / f"{self.disc_label}.dvdid.xml"
        if not to.suffix.lower().endswith(".xml"):
            to = to.with_suffix(f".{self.disc_label}.dvdid.xml")
        to.parent.mkdir(parents=True, exist_ok=True)
        return to.write_text(self.dumps(), encoding="utf8")

    def _get_files(self, iso_path: str) -> Iterator[DirectoryRecord]:
        """
        Yield all files in the device at the provided ISO path.
        Note: Special paths `.` and `..` paths are not yielded.
        """
        try:
            for dr in self.device.list_children(iso_path=iso_path):
                if dr.file_identifier().decode() in (".", ".."):
                    continue
                yield dr
        except PyCdlibInvalidInput:
            pass  # path probably doesnt exist

    def _get_first_64k_content(self, dr: DirectoryRecord) -> bytes:
        """
        Returns the first 65536 (or the file size, whichever is smaller) bytes of the file at the
        specified file path, as a bytearray.
        """
        read_size = min(dr.get_data_length(), 0x10000)

        f = BytesIO()
        self.device.get_file_from_iso_fp(
            outfp=f,
            iso_path=f"/VIDEO_TS/{dr.file_identifier().decode()}"
        )
        f.seek(0)
        content = f.read(read_size)

        if content is None or len(content) < read_size:
            raise EOFError(f"{read_size} bytes were expected, {len(content or [])} were read.")

        return content

    @staticmethod
    def _get_dr_name(dr: DirectoryRecord, as_string: bool = False) -> Union[bytearray, str]:
        """Get the name of the Directory Record as a UTF-8 bytearray terminated with a NUL character."""
        file_identifier = dr.file_identifier().decode()
        file_name = file_identifier.split(";")[0]  # remove ;N (file version)
        if as_string:
            return file_name
        utf8_name = bytearray(file_name, "utf8")
        utf8_name.append(0)
        return utf8_name

    @staticmethod
    def _get_dr_size(dr: DirectoryRecord) -> bytearray:
        """Get the size of the Directory Record formatted as a 4-byte unsigned integer bytearray."""
        file_size = bytearray(4)
        pack_into(b"I", file_size, 0, dr.get_data_length())
        return file_size

    @staticmethod
    def _get_dr_creation_time(dr: DirectoryRecord) -> bytearray:
        """
        Get the creation time in Microsoft FILETIME structure as a 8-byte unsigned integer bytearray.
        https://msdn.microsoft.com/en-us/library/windows/desktop/ms724284.aspx
        """
        dr_date = dr.date
        dr_date = datetime(
            year=1900 + dr_date.years_since_1900, month=dr_date.month, day=dr_date.day_of_month,
            hour=dr_date.hour, minute=dr_date.minute, second=dr_date.second,
            # offset the timezone, since ISO's dates are offsets of GMT in 15 minute intervals, we
            # need to calculate that but in seconds to pass to tzoffset.
            tzinfo=tzoffset("GMT", (15 * dr_date.gmtoffset) * 60)
        )

        epoch_offset = dr_date - datetime(1601, 1, 1, tzinfo=tzoffset(None, 0))
        creation_time_filetime = int(int(epoch_offset.total_seconds()) * (10 ** 7))

        file_creation_time = bytearray(8)
        pack_into(b"Q", file_creation_time, 0, creation_time_filetime)

        return file_creation_time
