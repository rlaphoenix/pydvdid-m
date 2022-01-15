from datetime import datetime
from inspect import cleandoc
from io import BytesIO
from pathlib import Path
from struct import pack_into
from typing import Union, Iterator

from dateutil.tz import tzoffset
from pycdlib import PyCdlib
from pycdlib.udf import UDFFileEntry

from pydvdid_m.crc64 import CRC64


class DvdId:
    def __init__(self, target: Union[str, PyCdlib]):
        """
        Computes a Windows API IDvdInfo2::GetDiscID-compatible 64-bit Cyclic Redundancy Check
        checksum from the DVD .vob, .ifo, and .bup files found in the supplied DVD device.
        """
        if not isinstance(target, PyCdlib):
            # assume str, open as a PyCdlib target
            device = PyCdlib()
            device.open(target)
        else:
            device = target
        self.device = device
        self.disc_label = self.device.pvd.volume_identifier.replace(b"\x00", b"").strip().decode()

        if not self.device.list_children(iso_path="/VIDEO_TS"):
            # Not a DVD-Video Disc?
            raise FileNotFoundError(f"The /VIDEO_TS directory and it's files doesn't exist in {target}")

        # the polynomial used for this CRC-64 checksum is:
        # x^63 + x^60 + x^57 + x^55 + x^54 + x^50 + x^49 + x^46 + x^41 + x^38 + x^37 + x^34 + x^32 +
        # x^31 + x^30 + x^28 + x^25 + x^24 + x^21 + x^16 + x^13 + x^12 + x^11 + x^08 + x^07 + x^05 + x^2
        crc = CRC64(0x92c64265d32139a4)

        for file in self._get_files("/VIDEO_TS"):
            crc.update(self._get_udf_creation_time(file))
            crc.update(self._get_udf_size(file))
            crc.update(self._get_udf_name(file))

        for file in self._get_files("/VIDEO_TS"):
            if self._get_udf_name(file, as_string=True).upper() in ("VIDEO_TS.IFO", "VTS_01_0.IFO"):
                crc.update(self._get_first_64k_content(file))

        self.checksum = crc

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

    def _get_files(self, iso_path: str) -> Iterator[UDFFileEntry]:
        """
        Yield all files in the device at the provided ISO path.
        Note, `.` and `..` paths are skipped.
        """
        for udf_entry in self.device.list_children(iso_path=iso_path):
            if udf_entry.file_identifier().decode() in (".", ".."):
                continue
            yield udf_entry

    def _get_first_64k_content(self, udf_entry: UDFFileEntry) -> bytes:
        """
        Returns the first 65536 (or the file size, whichever is smaller) bytes of the file at the
        specified file path, as a bytearray.
        """
        read_size = min(udf_entry.get_data_length(), 0x10000)

        f = BytesIO()
        self.device.get_file_from_iso_fp(
            outfp=f,
            iso_path=f"/VIDEO_TS/{udf_entry.file_identifier().decode()}"
        )
        f.seek(0)
        content = f.read(read_size)

        if content is None or len(content) < read_size:
            raise ValueError(f"{len(content or [])} bytes were expected, {read_size} were read.")

        return content

    @staticmethod
    def _get_udf_name(udf_entry: UDFFileEntry, as_string: bool = False) -> Union[bytearray, str]:
        """Get the name of the UDF Entry as a UTF-8 bytearray terminated with a NUL character."""
        file_identifier = udf_entry.file_identifier().decode()
        file_name = file_identifier.split(";")[0]  # remove ;N (file version)
        if as_string:
            return file_name
        utf8_name = bytearray(file_name, "utf8")
        utf8_name.append(0)
        return utf8_name

    @staticmethod
    def _get_udf_size(udf_entry: UDFFileEntry) -> bytearray:
        """Get the size of the UDF Entry formatted as a 4-byte unsigned integer bytearray."""
        file_size = bytearray(4)
        pack_into(b"I", file_size, 0, udf_entry.get_data_length())
        return file_size

    @staticmethod
    def _get_udf_creation_time(udf_entry: UDFFileEntry) -> bytearray:
        """
        Get the creation time in Microsoft FILETIME structure as a 8-byte unsigned integer bytearray.
        https://msdn.microsoft.com/en-us/library/windows/desktop/ms724284.aspx
        """
        udf_date = udf_entry.date  # type: ignore
        udf_date = datetime(
            year=1900 + udf_date.years_since_1900, month=udf_date.month, day=udf_date.day_of_month,
            hour=udf_date.hour, minute=udf_date.minute, second=udf_date.second,
            # offset the timezone, since ISO's dates are offsets of GMT in 15 minute intervals, we
            # need to calculate that but in seconds to pass to tzoffset.
            tzinfo=tzoffset("GMT", (15 * udf_date.gmtoffset) * 60)
        )

        epoch_offset = udf_date - datetime(1601, 1, 1, tzinfo=tzoffset(None, 0))
        creation_time_filetime = int(epoch_offset.total_seconds() * (10 ** 7))

        file_creation_time = bytearray(8)
        pack_into(b"Q", file_creation_time, 0, creation_time_filetime)

        return file_creation_time
