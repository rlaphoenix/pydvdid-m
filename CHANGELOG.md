# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added 

- This CHANGELOG file.
- Support for VIDEO_TS folders. However, they may not provide an accurate DvdId, see README.
- Added support for Path targets in disc_label. It returns the folder/file name as the disc label.
- Added file extension restrictions for files that get processed in DvdId (BUP, IFO, VOB).
- Added function `DvdId._get_file` to get a direct path (as the correct object type) to a specific file.

### Changed

- Refactored DvdId's class variable `disc_label` as a function property.
- Ensured that `VIDEO_TS.IFO` would be processed before `VTS_01_0.IFO`, and that they would both be processed.

### Fixed

- Fixed mistake in `DvdId._get_first_64k_content` which had the variables of the expected/read bytes mixed up.
- Fixed possible invalid creation time seconds value if it was somehow in floating-point accuracy. DVD IDs made
  from ISO files or straight from disc shouldn't have had any issues.
- Corrected the Type-hint of `UDFFileEntry` to `DirectoryRecord`.
- Added Error Handling to `DvdId._get_files`, which could cause an exception if the path isn't found.
- Fixed the `/VIDEO_TS` directory exists check in DvdId.

## [1.0.0] - 2022-01-15

### Added

- CRC64 class with various formatting helper functions within it.
- DvdId class that can generate a DVD ID for ISO files and direct from disc.
- Executable script via poetry that executes `DvdId.dump()` and `DvdId.dumps()` on the input.
- GitHub Workflows for CI/CD.
- Poetry Dependency Management and Building tooling.

[unreleased]: https://github.com/rlaphoenix/pydvdid-m/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/rlaphoenix/pydvdid-m/releases/tag/v1.0.0
