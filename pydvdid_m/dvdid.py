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
    def __init__(self, target: Union[str, PyCdlib], allow_folder_id: bool = False):
        """
        Computes a Windows API IDvdInfo2::GetDiscID-compatible 64-bit Cyclic Redundancy Check
        checksum from the DVD .vob, .ifo, and .bup files found in the supplied DVD device.
        """
        if isinstance(target, str):
            target_path = Path(target)
            if target_path.is_dir() and not target.startswith("\\\\.\\"):
                if allow_folder_id or input(
                    "Warning: Extracted VIDEO_TS folders most likely have modified file timestamps. "
                    "You may receive an inaccurate DVD ID if the timestamp does not match whats stated "
                    "in the original ISO 9660 headers.\n\n"
                    "Do you wish to continue anyway? (y/N): "
                ).lower() != "y":
                    return
                self.device = target_path
            else:
                # assume path to an ISO
                self.device = PyCdlib()
                self.device.open(target)
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
            if self._get_file_name(file, as_string=True).upper().split(".")[-1] in ("BUP", "IFO", "VOB"):
                crc.update(self._get_file_creation_time(file))
                crc.update(self._get_file_size(file))
                crc.update(self._get_file_name(file))

        crc.update(self._get_first_64k_content(self._get_file("/VIDEO_TS/VIDEO_TS.IFO")))
        crc.update(self._get_first_64k_content(self._get_file("/VIDEO_TS/VTS_01_0.IFO")))

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

    def dump(self, to: Union[Path, str]) -> Path:
        """
        Save DVD ID with Disc Label in XML format.

        Path can be to a direct file path or directory path.
        A custom filename using the Disc Label will be used for you
        if it's a path to a directory or non-XML file.

        Returns the Path where the DVD ID was saved.
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
        to.write_text(self.dumps(), encoding="utf8")
        return to

    def _get_files(self, iso_path: str) -> Iterator[DirectoryRecord]:
        """
        Yield all files in the device at the provided ISO path.
        Note: Special paths `.` and `..` paths are not yielded.
        """
        if isinstance(self.device, PyCdlib):
            try:
                for dr in self.device.list_children(iso_path=iso_path):
                    if dr.file_identifier().decode() in (".", ".."):
                        continue
                    yield dr
            except PyCdlibInvalidInput:
                pass  # path probably doesnt exist
        elif isinstance(self.device, Path):
            for file in (self.device / iso_path.lstrip("\\/")).iterdir():
                yield file
        else:
            raise ValueError(f"Target {self.device!r} unsupported.")

    def _get_file(self, iso_path: str) -> Union[DirectoryRecord, Path]:
        path = Path(iso_path.lstrip("\\/"))
        for file in self._get_files(f"/{path.parent}"):
            if self._get_file_name(file, as_string=True).upper() == path.name.upper():
                return file
        raise FileNotFoundError(f"File {path} could not be found.")

    def _get_first_64k_content(self, file: Union[DirectoryRecord, Path]) -> bytes:
        """
        Returns the first 65536 (or the file size, whichever is smaller) bytes of the file at the
        specified file path, as a bytearray.
        """
        if isinstance(file, DirectoryRecord):
            file_size = file.get_data_length()
        else:
            file_size = file.stat().st_size
        read_size = min(file_size, 0x10000)

        if isinstance(file, DirectoryRecord):
            f = BytesIO()
            self.device.get_file_from_iso_fp(
                outfp=f,
                iso_path=f"/VIDEO_TS/{file.file_identifier().decode()}"
            )
            f.seek(0)
            content = f.read(read_size)
        else:
            content = bytearray(read_size)
            with file.open("rb") as f:
                f.readinto(content)  # type: ignore

        if content is None or len(content) < read_size:
            raise EOFError(f"{read_size} bytes were expected, {len(content or [])} were read.")

        return content

    @staticmethod
    def _get_file_name(file: Union[Path, DirectoryRecord], as_string: bool = False) -> Union[bytearray, str]:
        """Get the name of the Directory Record as a UTF-8 bytearray terminated with a NUL character."""
        if isinstance(file, DirectoryRecord):
            file_identifier = file.file_identifier().decode()
            file_name = file_identifier.split(";")[0]  # remove ;N (file version)
        else:
            file_name = file.name
        file_name = file_name.upper()  # linux may allow it as other casing
        if as_string:
            return file_name
        utf8_name = bytearray(file_name, "utf8")
        utf8_name.append(0)
        return utf8_name

    @staticmethod
    def _get_file_size(file: Union[Path, DirectoryRecord]) -> bytearray:
        """Get the size of the Directory Record formatted as a 4-byte unsigned integer bytearray."""
        if isinstance(file, DirectoryRecord):
            file_size = file.get_data_length()
        else:
            file_size = file.stat().st_size
        array = bytearray(4)
        pack_into(b"I", array, 0, file_size)
        return array

    @staticmethod
    def _get_file_creation_time(file: Union[Path, DirectoryRecord]) -> bytearray:
        """
        Get the creation time in Microsoft FILETIME structure as a 8-byte unsigned integer bytearray.
        https://msdn.microsoft.com/en-us/library/windows/desktop/ms724284.aspx
        """
        if isinstance(file, DirectoryRecord):
            dr_date = file.date
            dr_date = datetime(
                year=1900 + dr_date.years_since_1900, month=dr_date.month, day=dr_date.day_of_month,
                hour=dr_date.hour, minute=dr_date.minute, second=dr_date.second,
                # offset the timezone, since ISO's dates are offsets of GMT in 15 minute intervals, we
                # need to calculate that but in seconds to pass to tzoffset.
                tzinfo=tzoffset("GMT", (15 * dr_date.gmtoffset) * 60)
            )
            epoch_offset = dr_date - datetime(1601, 1, 1, tzinfo=tzoffset(None, 0))
        else:
            # TODO: The created time may have been modified or even just differ after
            #       extraction, any difference to the true timestamp will return a
            #       different DVD ID. This is a problem.
            c_time = file.stat().st_ctime
            if c_time < -11644473600 or c_time >= 253402300800:
                raise ValueError(f"Created timestamp for file {file.name} is out of range: {c_time}")
            epoch_offset = datetime.utcfromtimestamp(c_time) - datetime(1601, 1, 1)

        filetime = int(int(epoch_offset.total_seconds()) * (10 ** 7))
        file_creation_time = bytearray(8)
        pack_into(b"Q", file_creation_time, 0, filetime)

        return file_creation_time
