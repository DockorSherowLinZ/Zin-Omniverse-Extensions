    from __future__ import annotations
    import omni.ext
    import omni.ui as ui

    from __future__ import annotations
import os, sys
from pathlib import Path

def _ensure_shared_on_path():
    # repo_root/exts/<ext_id>/python/.../extension.py -> go up to repo root
    this_file = Path(__file__).resolve()
    # climb until we find "exts" directory
    p = this_file
    repo_root = None
    for _ in range(8):
        if (p.parent / "exts").exists() and (p.parent / "shared").exists():
            repo_root = p.parent
            break
        p = p.parent
    if repo_root:
        shared_python = repo_root / "shared" / "tw.zin.smart_core" / "python"
        if shared_python.exists():
            sp = str(shared_python)
            if sp not in sys.path:
                sys.path.insert(0, sp)

_ensure_shared_on_path()


    from tw.zin.smart_core import get_logger, get_selected_prim_paths

    class SmartMeasureExtension(omni.ext.IExt):
        def on_startup(self, ext_id: str):
            self._log = get_logger("tw.zin.smart_measure")
            self._window = ui.Window("SmartMeasure", width=360, height=180, visible=False)
            with self._window.frame:
                with ui.VStack(spacing=8, height=0):
                    ui.Label("SmartMeasure", height=24)
                    ui.Button("Print selected prim paths", clicked_fn=self._on_print_selection)
                    ui.Separator()
                    ui.Label("Tip: Add <repo_root>/exts to Extension Search Paths.", word_wrap=True)

            # auto-show once on enable (you can remove this)
            self._window.visible = True
            self._log.info("Started")

        def on_shutdown(self):
            if getattr(self, "_window", None):
                self._window.visible = False
                self._window = None
            if getattr(self, "_log", None):
                self._log.info("Shutdown")

        def _on_print_selection(self):
            paths = get_selected_prim_paths()
            if not paths:
                self._log.info("No prim selected (or selection API not available).")
                return
            for p in paths:
                self._log.info(f"Selected: {p}")
