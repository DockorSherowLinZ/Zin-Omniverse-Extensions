from __future__ import annotations
from typing import List

def get_selected_prim_paths() -> List[str]:
    """Return selected prim paths (best-effort, works in Kit apps).
    If selection API isn't available, returns [].
    """
    try:
        import omni.usd
        ctx = omni.usd.get_context()
        sel = ctx.get_selection()
        return list(sel.get_selected_prim_paths())
    except Exception:
        return []
