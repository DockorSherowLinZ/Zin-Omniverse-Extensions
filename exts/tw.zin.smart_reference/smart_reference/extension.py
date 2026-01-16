import omni.ext
import omni.ui as ui
import omni.usd
from pxr import Sdf, Usd

# ========================================================
#  Smart Reference Widget
# ========================================================
class SmartReferenceWidget:
    def __init__(self):
        self._field_prefix = None
        self._field_url = None

    def startup(self):
        pass # 無需初始化

    def shutdown(self):
        pass # 無需清理

    def build_ui_layout(self):
        scroll_frame = ui.ScrollingFrame(
            horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
            vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED
        )
        with scroll_frame:
            # [修正] 靠上對齊
            with ui.VStack(spacing=10, padding=20, alignment=ui.Alignment.TOP):
                
                # --- Input Area ---
                ui.Label("Target Prefix (Parent/Name):", height=20, style={"color": 0xFFDDDDDD, "font_size": 14})
                self._field_prefix = ui.StringField(height=30)
                self._field_prefix.model.set_value("/World/Example")
                
                ui.Spacer(height=5)

                ui.Label("Asset URL (.usd):", height=20, style={"color": 0xFFDDDDDD, "font_size": 14})
                self._field_url = ui.StringField(height=30)
                self._field_url.model.set_value("omniverse://localhost/Projects/Asset.usd")

                ui.Spacer(height=15)

                # --- Button ---
                ui.Button(
                    "Auto Find & Reference", 
                    height=40, 
                    clicked_fn=self._on_apply_reference,
                    style={"background_color": 0xFF444444}
                )

                ui.Spacer(height=10)

                # --- Logic Description ---
                logic_text = "Logic: Finds the parent folder from your input, then searches ALL children starting with that name prefix."
                ui.Label(
                    logic_text, 
                    word_wrap=True, 
                    style={"color": 0xFF00AA00, "font_size": 14} 
                )
                
                ui.Spacer()
        return scroll_frame

    def _on_apply_reference(self):
        prefix_input = self._field_prefix.model.get_value_as_string().strip()
        asset_url = self._field_url.model.get_value_as_string().strip()

        if not prefix_input or not asset_url:
            print("[SmartReference] Error: Input fields cannot be empty.")
            return

        if "/" in prefix_input:
            parent_path, prefix_name = prefix_input.rsplit("/", 1)
            if not parent_path: parent_path = "/"
        else:
            parent_path = "/World"
            prefix_name = prefix_input

        print(f"[SmartReference] Searching in '{parent_path}' for children starting with '{prefix_name}'...")

        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        
        if not stage:
            print("[SmartReference] Error: No stage opened.")
            return

        parent_prim = stage.GetPrimAtPath(parent_path)
        if not parent_prim.IsValid():
            print(f"[SmartReference] Error: Parent prim '{parent_path}' not found.")
            return

        count = 0
        for child in parent_prim.GetChildren():
            if child.GetName().startswith(prefix_name):
                print(f"[SmartReference] Adding reference to: {child.GetPath()}")
                child.GetReferences().ClearReferences()
                child.GetReferences().AddReference(asset_url)
                count += 1

        print(f"[SmartReference] Done. Updated {count} prims.")


# ========================================================
#  Extension Wrapper
# ========================================================
class SmartReferenceExtension(omni.ext.IExt):
    WINDOW_NAME = "Smart Reference"
    MENU_PATH = f"Zin Tools/{WINDOW_NAME}"

    def __init__(self):
        super().__init__()
        self._widget = SmartReferenceWidget()
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