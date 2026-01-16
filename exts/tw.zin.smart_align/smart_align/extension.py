import omni.ext
import omni.ui as ui
import omni.usd
from pxr import Usd, UsdGeom, Gf

# ========================================================
#  Smart Align Widget
# ========================================================
class SmartAlignWidget:
    def __init__(self):
        self._usd_context = omni.usd.get_context()

    def startup(self):
        pass

    def shutdown(self):
        pass

    def build_ui_layout(self):
        scroll_frame = ui.ScrollingFrame(
            horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
            vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED
        )
        with scroll_frame:
            # [修正] 靠上對齊
            with ui.VStack(spacing=10, padding=20, alignment=ui.Alignment.TOP):
                
                ui.Label("Align Selection", height=20, style={"color": 0xFFDDDDDD, "font_size": 14})
                ui.Spacer(height=5)

                with ui.HStack(height=40, spacing=10):
                    ui.Button("Min X", clicked_fn=lambda: self._align_op(0, 'min'))
                    ui.Button("Center X", clicked_fn=lambda: self._align_op(0, 'center'))
                    ui.Button("Max X", clicked_fn=lambda: self._align_op(0, 'max'))

                with ui.HStack(height=40, spacing=10):
                    ui.Button("Min Y", clicked_fn=lambda: self._align_op(1, 'min'))
                    ui.Button("Center Y", clicked_fn=lambda: self._align_op(1, 'center'))
                    ui.Button("Max Y", clicked_fn=lambda: self._align_op(1, 'max'))

                with ui.HStack(height=40, spacing=10):
                    ui.Button("Min Z", clicked_fn=lambda: self._align_op(2, 'min'))
                    ui.Button("Center Z", clicked_fn=lambda: self._align_op(2, 'center'))
                    ui.Button("Max Z", clicked_fn=lambda: self._align_op(2, 'max'))

                ui.Spacer(height=10)
                ui.Button("Drop to Ground", height=40, clicked_fn=self._drop_to_ground, style={"background_color": 0xFF444444})
                
                ui.Spacer()
        return scroll_frame

    def _align_op(self, axis, mode):
        # 簡單的對齊邏輯實作
        stage = self._usd_context.get_stage()
        paths = self._usd_context.get_selection().get_selected_prim_paths()
        if len(paths) < 2: return

        # 最後選取的當作 Target (簡單邏輯)
        target_prim = stage.GetPrimAtPath(paths[-1])
        target_xform = UsdGeom.Xformable(target_prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        target_trans = target_xform.ExtractTranslation()

        for p in paths[:-1]:
            prim = stage.GetPrimAtPath(p)
            xform_api = UsdGeom.XformCommonAPI(prim)
            t, r, s, p_rot, r_ord = xform_api.GetXformVectors(Usd.TimeCode.Default())
            
            new_pos = Gf.Vec3d(t)
            new_pos[axis] = target_trans[axis] # 這裡簡化為 Pivot 對齊
            
            xform_api.SetTranslate(new_pos)

    def _drop_to_ground(self):
        # 簡單的落地邏輯
        stage = self._usd_context.get_stage()
        paths = self._usd_context.get_selection().get_selected_prim_paths()
        for p in paths:
            prim = stage.GetPrimAtPath(p)
            xform_api = UsdGeom.XformCommonAPI(prim)
            t, _, _, _, _ = xform_api.GetXformVectors(Usd.TimeCode.Default())
            new_pos = Gf.Vec3d(t)
            new_pos[2] = 0.0 # 假設 Z-up, 地板在 0
            xform_api.SetTranslate(new_pos)


# ========================================================
#  Extension Wrapper
# ========================================================
class SmartAlignExtension(omni.ext.IExt):
    WINDOW_NAME = "Smart Align"
    MENU_PATH = f"Zin Tools/{WINDOW_NAME}"

    def __init__(self):
        super().__init__()
        self._widget = SmartAlignWidget()
        self._window = None
        self._menu_added = False

    def on_startup(self, ext_id):
        self._build_menu()

    def on_shutdown(self):
        self._remove_menu()
        if self._widget: self._widget.shutdown()
        if self._window: self._window.destroy(); self._window = None

    def _build_menu(self):
        try:
            m = omni.kit.ui.get_editor_menu()
            if m: m.add_item(self.MENU_PATH, self._toggle_window, toggle=True, value=False)
            self._menu_added = True
        except: pass

    def _remove_menu(self):
        try:
            m = omni.kit.ui.get_editor_menu()
            if m and m.has_item(self.MENU_PATH): m.remove_item(self.MENU_PATH)
        except: pass

    def _toggle_window(self, menu, value):
        if value:
            if not self._window:
                self._window = ui.Window(self.WINDOW_NAME, width=400, height=400)
                self._window.set_visibility_changed_fn(self._on_visibility_changed)
                with self._window.frame:
                    self._widget.build_ui_layout()
            self._window.visible = True
        else:
            if self._window: self._window.visible = False

    def _on_visibility_changed(self, visible):
        if self._menu_added:
            try: omni.kit.ui.get_editor_menu().set_value(self.MENU_PATH, bool(visible))
            except: pass

    # --- Bridge Methods ---
    def startup_logic(self): self._widget.startup()
    def shutdown_logic(self): self._widget.shutdown()
    def build_ui_layout(self): return self._widget.build_ui_layout()