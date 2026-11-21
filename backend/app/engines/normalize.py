"""Merchant normalization. Owner: Vaishnavi. TODO(slice 1).

Pure functions, no I/O, easy to unit test.
"""

from __future__ import annotations


def normalize_merchant(raw_desc: str) -> str:
    """'UPI/NETFLIX/netflix@icici/Payment' -> 'netflix'; 'POS 4471 MUMBAI' -> 'pos 4471 mumbai'.

    Suggested steps: lowercase; strip channel prefixes (UPI/, POS, NEFT/, IMPS/, ACH D-, BBPS);
    drop ref numbers / VPA handles / city suffixes; collapse whitespace. TODO(slice 1)
    """
    raise NotImplementedError
