"""
matrix.py -- Cauchy encoding matrix construction over GF(2^8).

A Cauchy matrix M has the property that every square sub-matrix is invertible,
which guarantees that any m rows (fragments) of the codeword suffice to
reconstruct the original data.  Entry (i, j) is:

    M[i][j] = 1 / (x_i + y_j)   in GF(2^8)

where {x_i} and {y_j} are disjoint sets of field elements.

Alternatively, a systematic Vandermonde matrix can be used, but the Cauchy
construction gives a cleaner inversion guarantee.

References:
    - Blömer et al., "An XOR-based erasure-resilient coding scheme" (1995)
    - `galois` library docs for GF(2^8) matrix operations
"""

from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import galois  # type: ignore[import]

from src.fingerprint.field import gf_add, gf_inv, gf_mul, gf_div


class CodingMatrix:
    """A Cauchy matrix over GF(2^8) used as the erasure encoding matrix.

    Attributes:
        m (int): Number of source (data) symbols (reconstruction threshold).
        n (int): Total number of coded symbols (fragments).
        matrix: An n×m matrix over GF(2^8) (galois.GF(256) array).
    """

    def __init__(self, m: int, n: int) -> None:
        """Build the n×m Cauchy encoding matrix.

        Chooses disjoint x-points {1, ..., n} and y-points {n+1, ..., n+m}
        in GF(2^8).  Requires n + m <= 256.

        Args:
            m: Number of data symbols (columns).
            n: Number of coded fragments (rows).

        Raises:
            ValueError: If n + m > 256 (not enough distinct field elements).
        """
        # Validate m and n and store
        if m <= 0 or n <= 0:
            raise ValueError(f"m and n must be positive; m={m}, n={n}")
        if m > n:
            raise ValueError(f"m must be <= n; m={m}, n={n}")
        if n + m > 255:
            raise ValueError(f"n + m must be <= 255; n={n}, m={m}, n+m={n+m}")

        self.m = m
        self.n = n

        # Setup matrix:
        # x_i = i for i in 1..n (row points)
        # y_j = n + j for j in 1..m (column points)
        # M[i][j] = 1 / (x_i ^ y_j) in GF(2^8)

        self._matrix: list[list[int]] = [
            [gf_inv(gf_add(i, n + j)) for j in range(1, m + 1)]
            for i in range (1, n + 1)
        ]

    def encode(self, data_symbols: list[int]) -> list[int]:
        """Multiply the encoding matrix by a column of data symbols.

        Args:
            data_symbols: A length-m array of GF(2^8) elements (one per
                          data symbol / chunk).

        Returns:
            A length-n array of coded fragments.
        """
        if len(data_symbols) != self.m:
            raise ValueError(f"data_symbols length {len(data_symbols)} does not match m={self.m}")

        result = []
        for i in range(self.n):
            acc = 0
            for j in range(self.m):
                acc ^= gf_mul(self._matrix[i][j], data_symbols[j])
            result.append(acc)
        return result

    def submatrix(self, row_indices: list[int]) -> CodingMatrix:
        """Extract a square sub-matrix for decoding.

        Args:
            row_indices: Indices of the m available fragments (0-based).

        Returns:
            A new CodingMatrix wrapping the m×m sub-matrix.

        Raises:
            ValueError: If len(row_indices) != m.
        """
        if len(row_indices) != self.m:
            raise ValueError(f"expected {self.m} row indices, got {len(row_indices)}")
        
        obj = object.__new__(CodingMatrix)
        obj.m = self.m
        obj.n = self.m
        obj._matrix = [self._matrix[i] for i in row_indices]

        return obj

    def invert(self) -> CodingMatrix:
        """Compute the matrix inverse over GF(2^8).

        Only valid when the matrix is square (m×m sub-matrix for decoding).

        Returns:
            A new CodingMatrix wrapping the inverse.

        Raises:
            ValueError: If the matrix is not square.
            np.linalg.LinAlgError: If the matrix is singular (should not
                happen for a Cauchy matrix).
        """
        if self.n != self.m:
            raise ValueError(f"matrix must be square to invert; got {self.n}x{self.m}")
        
        size = self.m

        # Build augmented matrix [A | I]
        aug = [
            row[:] + [1 if i == j else 0 for j in range(size)]
            for i, row in enumerate(self._matrix)
        ]

        for col in range(size):
            # Find non-zero pivot in column
            pivot = next((r for r in range(col, size) if aug[r][col] != 0), None)
            if pivot is None:
                raise ValueError("matrix is singlular")
            aug[col], aug[pivot] = aug[pivot], aug[col]

            # Scale pivot row so the diagonal element becomes 1
            scale = gf_inv(aug[col][col])
            aug[col] = [gf_mul(scale, x) for x in aug[col]]

            for row in range(size):
                if row != col and aug[row][col] != 0:
                    factor = aug[row][col]
                    aug[row] = [aug[row][k] ^ gf_mul(factor, aug[col][k]) for k in range(2 * size)]

        obj = object.__new__(CodingMatrix)
        obj.m = self.m
        obj.n = self.m
        obj._matrix = [row[size:] for row in aug]
        return obj