"""
test_matrix.py -- Unit tests for the Cauchy encoding matrix.

Covers:
    - Matrix has correct shape (n rows × m cols)
    - Every m×m sub-matrix is invertible (key Cauchy property)
    - submatrix() returns correct rows
    - invert() * original == identity
    - encode() produces correct length output
"""

import pytest
from itertools import combinations
from src.erasure.matrix import CodingMatrix


class TestCodingMatrixShape:
    """Shape and construction tests."""

    def test_matrix_dimensions(self):
        """CodingMatrix(m=3, n=5) has 5 rows and 3 columns."""
        # TODO: mat = CodingMatrix(m=3, n=5)
        #       assert mat.matrix.shape == (5, 3)
        ...

    def test_n_plus_m_exceeds_256_raises(self):
        """Construction raises ValueError when n + m > 256."""
        # TODO: with pytest.raises(ValueError): CodingMatrix(m=200, n=100)
        ...


class TestCauchyInvertibility:
    """Every m×m sub-matrix of a Cauchy matrix must be invertible."""

    def test_all_square_submatrices_invertible(self):
        """For 3-of-5, all C(5,3)=10 sub-matrices are invertible."""
        # TODO: mat = CodingMatrix(m=3, n=5)
        #       for row_subset in combinations(range(5), 3):
        #           sub = mat.submatrix(list(row_subset))
        #           inv = sub.invert()   # should not raise
        #           # verify sub @ inv == identity
        ...


class TestCodingMatrixEncode:
    """Tests for the encode() method."""

    def test_encode_output_length(self):
        """encode() returns an array of length n."""
        # TODO: import numpy as np, galois
        #       GF = galois.GF(256)
        #       mat = CodingMatrix(m=3, n=5)
        #       data_symbols = GF([1, 2, 3])
        #       coded = mat.encode(data_symbols)
        #       assert len(coded) == 5
        ...
