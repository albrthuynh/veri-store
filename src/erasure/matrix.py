from __future__ import annotations

from src.fingerprint.field import gf_add, gf_inv, gf_mul


class CodingMatrix:
    def __init__(self, m: int, n: int) -> None:
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

        self._matrix = []

        # First m rows: identity
        for i in range(m):
            self._matrix.append([1 if j == i else 0 for j in range(m)])

        # Last n-m rows: Cauchy parity
        # row points: m+1 .. n, column points: 1 .. m  (all distinct, no overlap)
        for i in range(1, n - m + 1):
            self._matrix.append([gf_inv(gf_add(m + i, j)) for j in range(1, m + 1)])

    def encode(self, data_symbols: list[int]) -> list[int]:
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
        if len(row_indices) != self.m:
            raise ValueError(f"expected {self.m} row indices, got {len(row_indices)}")
        
        obj = object.__new__(CodingMatrix)
        obj.m = self.m
        obj.n = self.m
        obj._matrix = [self._matrix[i] for i in row_indices]

        return obj

    def invert(self) -> CodingMatrix:
        if self.n != self.m:
            raise ValueError(f"matrix must be square to invert; got {self.n}x{self.m}")
        
        size = self.m

        # Build augmented matrix [A | I].
        aug = [
            row[:] + [1 if i == j else 0 for j in range(size)]
            for i, row in enumerate(self._matrix)
        ]

        for col in range(size):
            # Find a non-zero pivot in this column.
            pivot = next((r for r in range(col, size) if aug[r][col] != 0), None)
            if pivot is None:
                raise ValueError("matrix is singlular")
            aug[col], aug[pivot] = aug[pivot], aug[col]

            # Scale the pivot row so the diagonal entry becomes 1.
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
