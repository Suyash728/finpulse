"""Supabase client (service key, server-side only). Owner: Vaishnavi.

Single-user demo: no RLS, no auth. Never expose SUPABASE_SERVICE_KEY to the frontend.
"""

from __future__ import annotations

import os
from functools import cache


@cache
def get_client():
    """Return a cached supabase.Client built from SUPABASE_URL + SUPABASE_SERVICE_KEY.

    Imported lazily so tests and /health run without Supabase installed or configured.
    Usage: get_client().table("transactions").select("*").eq("needs_review", True).execute().data
    """
    from supabase import create_client  # lazy import

    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY not set")
    return create_client(url, key)
