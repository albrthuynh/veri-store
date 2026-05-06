from itertools import combinations

import pytest

from src.erasure.matrix import CodingMatrix
from src.fingerprint.field import GF256


def matrix_rows(matrix_like) -> list[list[int]]:
    """Return matrix contents as a list of rows containing plain ints."""
    raw_matrix = matrix_like._matrix

    if hasattr(raw_matrix, "tolist"):
        raw_matrix = raw_matrix.tolist()

    rows: list[list[int]] = []
    for row in raw_matrix:
        converted_row: list[int] = []
        for value in row:
            converted_row.append(int(value))
        rows.append(converted_row)

    return rows


def vector_values(vector_like) -> list[int]:
    """Return vector contents as a list of plain ints."""
    if hasattr(vector_like, "tolist"):
        vector_like = vector_like.tolist()

    values: list[int] = []
    for value in vector_like:
        values.append(int(value))

    return values


def multiply_matrices(
    left_matrix: list[list[int]],
    right_matrix: list[list[int]],
) -> list[list[int]]:
    """Multiply two matrices over GF(2^8)."""
    result: list[list[int]] = []
    right_column_count = len(right_matrix[0])

    for left_row in left_matrix:
        result_row: list[int] = []
        for column_index in range(right_column_count):
            total = 0
            for shared_index, left_value in enumerate(left_row):
                right_value = right_matrix[shared_index][column_index]
                product = int(GF256(left_value) * GF256(right_value))
                total = total ^ product
            result_row.append(total)
        result.append(result_row)

    return result


def identity_matrix(size: int) -> list[list[int]]:
    """Return an identity matrix using plain int field elements."""
    rows: list[list[int]] = []

    for row_index in range(size):
        row: list[int] = []
        for column_index in range(size):
            if row_index == column_index:
                row.append(1)
            else:
                row.append(0)
        rows.append(row)

    return rows


class TestCodingMatrixShape:
    def test_matrix_dimensions(self):
        """CodingMatrix(m=3, n=5) has 5 rows and 3 columns."""
        matrix = CodingMatrix(m=3, n=5)
        rows = matrix_rows(matrix)

        assert len(rows) == 5
        assert all(len(row) == 3 for row in rows)

    def test_first_m_rows_are_identity(self):
        """The first m rows are identity rows for systematic encoding."""
        matrix = CodingMatrix(m=3, n=5)
        rows = matrix_rows(matrix)

        assert rows[:3] == identity_matrix(3)

    def test_m_greater_than_n_raises_value_error(self):
        """Construction rejects thresholds larger than the fragment count."""
        with pytest.raises(ValueError):
            CodingMatrix(m=4, n=3)

    def test_field_size_limit_raises_value_error(self):
        """Construction rejects parameters that exceed GF(2^8) limits."""
        with pytest.raises(ValueError):
            CodingMatrix(m=200, n=100)


class TestCodingMatrixSubmatrix:
    """Tests for extracting matrix rows by fragment index."""

    def test_submatrix_returns_requested_rows(self):
        """submatrix() preserves row order and contents."""
        matrix = CodingMatrix(m=3, n=5)
        rows = matrix_rows(matrix)

        submatrix = matrix.submatrix([4, 0, 2])
        submatrix_rows = matrix_rows(submatrix)

        assert submatrix_rows == [rows[4], rows[0], rows[2]]

    def test_submatrix_requires_m_rows(self):
        """submatrix() rejects row selections that are not square."""
        matrix = CodingMatrix(m=3, n=5)

        with pytest.raises(ValueError):
            matrix.submatrix([0, 1])

        with pytest.raises(ValueError):
            matrix.submatrix([0, 1, 2, 3])


class TestCodingMatrixInvertibility:
    """Every m-row subset must be enough to decode."""

    def test_all_square_submatrices_are_invertible(self):
        """For 3-of-5, all C(5, 3)=10 row subsets are invertible."""
        matrix = CodingMatrix(m=3, n=5)

        for row_subset in combinations(range(5), 3):
            submatrix = matrix.submatrix(list(row_subset))
            inverse = submatrix.invert()
            product = multiply_matrices(matrix_rows(inverse), matrix_rows(submatrix))

            assert product == identity_matrix(3)

    def test_inverse_times_matrix_gives_identity(self):
        """invert() returns a true inverse over GF(2^8)."""
        matrix = CodingMatrix(m=3, n=5)
        submatrix = matrix.submatrix([4, 2, 0])

        inverse = submatrix.invert()
        product = multiply_matrices(matrix_rows(inverse), matrix_rows(submatrix))

        assert product == identity_matrix(3)

    def test_non_square_matrix_cannot_be_inverted(self):
        """invert() rejects the full n x m coding matrix."""
        matrix = CodingMatrix(m=3, n=5)

        with pytest.raises(ValueError):
            matrix.invert()


class TestCodingMatrixEncode:
    """Tests for the encode() method."""

    def test_encode_output_length(self):
        """encode() returns one coded symbol per matrix row."""
        matrix = CodingMatrix(m=3, n=5)

        coded_symbols = vector_values(matrix.encode([1, 2, 3]))

        assert len(coded_symbols) == 5

    def test_encode_is_systematic(self):
        """The first m encoded symbols are the original source symbols."""
        matrix = CodingMatrix(m=3, n=5)
        source_symbols = [17, 34, 51]

        coded_symbols = vector_values(matrix.encode(source_symbols))

        assert coded_symbols[:3] == source_symbols
