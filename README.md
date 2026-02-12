This is a project made by Albert and Mac for CS588

## Important Values:
- m-of-n: A block of data B can be split into n fragments in such a way that it can be rebuilt with only m of the fragments.
- f: The number of fragments which can be unavailable for the system to still work (fault tolerance)
- m $\geq$ f + 1
- n = m + 2f

## Libraries to use:
- [hashlib](https://docs.python.org/3/library/hashlib.html) - for running hash algorithms (including SHA256) in Python
- [cryptography](https://pypi.org/project/cryptography/) - various cryptographic primitives for Python
- [galois](https://pypi.org/project/galois/) - finite field arithmetic
- [numpy](https://numpy.org/) - efficient array operations for polynomial manipulation