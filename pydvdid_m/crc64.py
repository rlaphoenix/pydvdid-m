from __future__ import annotations

import struct
from typing import Union


class CRC64:
    def __init__(self, polynomial: int, initial_xor: int = 0xffffffffffffffff):
        """
        Calculates a 64-bit Cyclic Redundancy Check checksum.

        Requires a polynomial to seed the construction of a lookup table and an
        optional initial XOR value.
        """
        if not isinstance(polynomial, int):
            raise ValueError(f"Polynomial must be an integer, not {polynomial!r}.")
        if not isinstance(initial_xor, int):
            raise ValueError(f"Initial XOR must be an integer, not {initial_xor!r}.")

        self._polynomial = polynomial
        self._initial_xor = initial_xor

        self._lookup_table = self._construct_lookup_table(polynomial)
        self._checksum = initial_xor

    def __eq__(self, other: CRC64) -> bool:
        return self._checksum == other._checksum

    def __ne__(self, other: CRC64) -> bool:
        return not self.__eq__(other)

    def __str__(self) -> str:
        return f"{self.high_bytes}|{self.low_bytes}"

    def __repr__(self) -> str:
        return f"<CRC64 " \
               f"polynomial=0x{self._polynomial:016x} " \
               f"xor=0x{self._initial_xor:016x} " \
               f"checksum=0x{self._checksum:016x}" \
               ">"

    @property
    def high_bytes(self) -> str:
        """Topmost 4 bytes of the checksum formatted as a lowercase hex string."""
        return format(self._checksum >> 32, "08x")

    @property
    def low_bytes(self) -> str:
        """Bottommost 4 bytes of the checksum formatted as a lowercase hex string."""
        return format(self._checksum & 0xffffffff, "08x")

    @property
    def as_bytes(self) -> bytes:
        """Checksum represented as bytes."""
        return struct.pack(">Q", self._checksum)

    def update(self, data: Union[bytes, bytearray]) -> None:
        """Enumerate the bytes of the supplied bytearray and update the CRC-64 in-place."""
        if not isinstance(data, (bytes, bytearray)):
            raise ValueError(f"Data must be a byte array, not {data!r}.")

        for byte in data:
            self._checksum = (self._checksum >> 8) ^ self._lookup_table[(self._checksum & 0xff) ^ byte]

    @staticmethod
    def _construct_lookup_table(polynomial: int) -> list[int]:
        """Precomputes the CRC-64 lookup table seeded from the supplied polynomial."""
        if not isinstance(polynomial, int):
            raise ValueError(f"Polynomial must be an integer, not {polynomial!r}.")

        lookup_table = []
        for i in range(0, 256):
            lookup_value = i
            for _ in range(0, 8):
                if lookup_value & 0x1 == 0x1:
                    lookup_value = (lookup_value >> 1) ^ polynomial
                else:
                    lookup_value = lookup_value >> 1
            lookup_table.append(lookup_value)
        return lookup_table
