import math
 
import omni.ext
import omni.ui as ui
import omni.kit.ui
import omni.kit.app
import omni.usd
from omni.ui import DockPreference
from pxr import Usd, UsdGeom, Gf
 
try:
    import omni.kit.clipboard as clipboard
except Exception:
    clipboard = None
 
 
class SmartMeasureExtension(omni.ext.IExt):
    WINDOW_NAME = "Smart Measure"
    MENU_PATH = f"Zin Tools/{WINDOW_NAME}"
 
    # 常見 metersPerUnit 對應名稱
    METERS_PER_UNIT_TO_NAME = {
        1.0: "m",
        0.1: "dm",
        0.01: "cm",
        0.001: "mm",
        0.0254: "inch",
        0.3048: "ft",
    }
 
    # 顯示用單位（不改變 stage）
    DISPLAY_UNITS = [
        ("mm", 0.001),
        ("cm", 0.01),
        ("m", 1.0),
        ("inch", 0.0254),
        ("ft", 0.3048),
    ]
 
    # ---------------- lifecycle ----------------
    def on_startup(self, ext_id):
        self._usd_context = omni.usd.get_context()
 
        # 狀態
        self._last_size_m = None           # (x, y, z) in meters；多選=聯合集合的外框尺寸
        self._last_count = 0
        self._stage_mpu = 1.0
        self._stage_unit_name = "m"
        self._up_axis = "Z"
        self._display_unit = "cm"
        self._display_mpu = 0.01
 
        # 訂閱與選單狀態
        self._stage_event_sub = None
        self._sel_event_sub = None
        self._poll_update_sub = None
        self._last_sel_key = ""
        self._menu_added = False
 
        self._build_menu()
        self._build_window()
        self._subscribe_events()
 
        self._refresh_stage_info()
        self._update_all_labels(clear=True)
        self._render_selected_paths([])
 
    def on_shutdown(self):
        # 只有成功新增選單時才移除，避免 not found 警告
        try:
            if self._menu_added:
                editor_menu = omni.kit.ui.get_editor_menu()
                if editor_menu and hasattr(editor_menu, "has_item") and editor_menu.has_item(self.MENU_PATH):
                    editor_menu.remove_item(self.MENU_PATH)
        except Exception:
            pass
 
        self._stage_event_sub = None
        self._sel_event_sub = None
        self._poll_update_sub = None
        self._window = None
 
    # ---------------- UI ----------------
    def _build_menu(self):
        try:
            editor_menu = omni.kit.ui.get_editor_menu()
            if editor_menu:
                editor_menu.add_item(self.MENU_PATH, self._toggle_window, toggle=True, value=True)
                self._menu_added = True
        except Exception:
            self._menu_added = False
 
    def _build_window(self):
        self._window = ui.Window(
            SmartMeasureExtension.WINDOW_NAME,
            width=320,
            height=520,
            dockPreference=DockPreference.RIGHT,
        )
        self._window.set_visibility_changed_fn(self._on_visibility_changed)
 
        with self._window.frame:
            with ui.VStack(spacing=8, height=ui.Fraction(1), padding=8):
 
                # ---------- Selected ----------
                with ui.CollapsableFrame("Selected", collapsed=False, name="section_selected"):
                    with ui.VStack(spacing=6, padding=6):
                        with ui.HStack():
                            ui.Label("Prim", width=60)
                            # 深色底塊（無滑桿）：固定高度 + 自動換行
                            with ui.Frame(height=120):
                                self._sel_paths_label = ui.Label(
                                    "",
                                    word_wrap=True,
                                    alignment=ui.Alignment.LEFT_TOP,
                                )
 
                # ---------- Dimensions ----------
                with ui.CollapsableFrame("Dimensions", collapsed=False, name="section_dims", height=ui.Fraction(1)):
                    # 整個內容（含按鈕）都放在框內
                    with ui.Frame(height=ui.Fraction(1)):
                        with ui.VStack(spacing=8, padding=6):
                            ui.Label("Results")
                            with ui.HStack():
                                with ui.VStack(spacing=2):
                                    self._len_label = ui.Label("X length: --")
                                    self._wid_label = ui.Label("Y width : --")
                                    self._hei_label = ui.Label("Z height: --")
                                ui.Spacer()
                                ui.Button("Copy", width=80, clicked_fn=self._copy_result)
 
                            with ui.HStack():
                                ui.Label("Units", width=60)
                                items = [u[0] for u in self.DISPLAY_UNITS]
                                default_index = 1  # cm
                                self._unit_combo = ui.ComboBox(default_index, *items)
                                self._unit_combo.model.get_item_value_model().add_value_changed_fn(
                                    self._on_display_unit_changed
                                )
 
                            with ui.HStack(spacing=6):
                                ui.Spacer()
                                ui.Button("Refresh", width=100, clicked_fn=self._refresh_and_measure)
                                ui.Button("Clear", width=100, clicked_fn=self._on_clear)
 
                # Dimensions 與下方黑底線距離 24px
                ui.Spacer(height=24)
                ui.Line()
 
                # Footer：兩行間距 8px
                with ui.VStack(spacing=8, padding=2):
                    with ui.HStack():
                        ui.Label("Stage unit :", width=80)
                        self._stage_unit_label = ui.Label("m")
                    with ui.HStack():
                        ui.Label("Up-Axis    :", width=80)
                        self._up_axis_label = ui.Label("Z")
 
    # ---------------- events ----------------
    def _subscribe_events(self):
        # Stage events
        stream = self._usd_context.get_stage_event_stream()
        self._stage_event_sub = stream.create_subscription_to_pop(
            self._on_stage_event, name="smart_measure_stage"
        )
 
        # Selection events（相容不同 API 名稱）
        sel = self._usd_context.get_selection()
        names = [
            "get_on_change_fn_stream",
            "get_on_changed_fn_stream",
            "get_change_event_stream",
            "get_selection_changed_event_stream",
        ]
        self._sel_event_sub = None
        for n in names:
            try:
                getter = getattr(sel, n, None)
                if getter:
                    ev = getter()
                    self._sel_event_sub = ev.create_subscription_to_pop(
                        self._on_selection_changed, name="smart_measure_selection"
                    )
                    break
            except Exception:
                self._sel_event_sub = None
 
        # Poll fallback
        if not self._sel_event_sub:
            app = omni.kit.app.get_app()
            update_stream = app.get_update_event_stream()
            self._poll_counter = 0
 
            def on_update(_):
                self._poll_counter += 1
                if self._poll_counter % 8 != 0:
                    return
                self._check_selection_poll()
 
            self._poll_update_sub = update_stream.create_subscription_to_pop(
                on_update, name="smart_measure_poll"
            )
 
    def _toggle_window(self, menu, value):
        if self._window:
            self._window.visible = bool(value)
 
    def _on_visibility_changed(self, visible):
        if not self._menu_added:
            return
        try:
            editor_menu = omni.kit.ui.get_editor_menu()
            if editor_menu:
                editor_menu.set_value(self.MENU_PATH, bool(visible))
        except Exception:
            pass
 
    def _on_stage_event(self, event):
        t = event.type
        if t == int(omni.usd.StageEventType.OPENED):
            self._refresh_stage_info()
            self._update_all_labels(clear=True)
            self._render_selected_paths([])
        elif t == int(omni.usd.StageEventType.CLOSING):
            self._last_size_m = None
            self._last_count = 0
            self._stage_mpu = 1.0
            self._stage_unit_name = "m"
            self._up_axis = "Z"
            self._refresh_footer()
            self._update_all_labels(clear=True)
            self._render_selected_paths([])
 
    def _on_selection_changed(self, _):
        self._sync_selection_and_measure()
 
    def _check_selection_poll(self):
        paths = self._usd_context.get_selection().get_selected_prim_paths()
        key = "|".join(paths) if paths else ""
        if key != self._last_sel_key:
            self._last_sel_key = key
            self._sync_selection_and_measure()
 
    def _sync_selection_and_measure(self):
        paths = self._usd_context.get_selection().get_selected_prim_paths()
        self._render_selected_paths(paths)
        if paths:
            self._measure_paths(paths)
 
    # ---------------- selected list (no scrollbar) ----------------
    def _render_selected_paths(self, paths):
        # 無滑桿：固定高度區塊 + 自動換行
        self._sel_paths_label.text = "\n".join(paths) if paths else ""
 
    # ---------------- units/footer ----------------
    def _on_display_unit_changed(self, model, _=None):
        idx = model.get_value_as_int()
        idx = max(0, min(idx, len(self.DISPLAY_UNITS) - 1))
        name, mpu = self.DISPLAY_UNITS[idx]
        self._display_unit = name
        self._display_mpu = mpu
        self._update_all_labels()
 
    def _format_stage_unit(self, mpu: float) -> str:
        # 常見值直接顯示縮寫；否則以「無條件進位到小數點後兩位」的公尺值
        if mpu in self.METERS_PER_UNIT_TO_NAME:
            return self.METERS_PER_UNIT_TO_NAME[mpu]
        v = math.ceil(float(mpu) * 100) / 100.0
        return f"{v:.2f} m"
 
    def _refresh_stage_info(self):
        stage = self._usd_context.get_stage()
        if stage:
            mpu = UsdGeom.GetStageMetersPerUnit(stage) or 1.0
            self._stage_mpu = float(mpu)
            self._stage_unit_name = self._format_stage_unit(self._stage_mpu)
            try:
                axis_token = UsdGeom.GetStageUpAxis(stage)
                self._up_axis = "Z" if axis_token == UsdGeom.Tokens.z else "Y"
            except Exception:
                self._up_axis = "Z"
        else:
            self._stage_mpu = 1.0
            self._stage_unit_name = self._format_stage_unit(self._stage_mpu)
            self._up_axis = "Z"
        self._refresh_footer()
 
    def _refresh_footer(self):
        self._stage_unit_label.text = self._stage_unit_name
        self._up_axis_label.text = self._up_axis
 
    # ---------------- measure (multi-select = union world AABB) ----------------
    def _refresh_and_measure(self):
        self._refresh_stage_info()
        paths = self._usd_context.get_selection().get_selected_prim_paths()
        if paths:
            self._measure_paths(paths)
 
    def _measure_paths(self, paths):
        stage = self._usd_context.get_stage()
        if not stage or not paths:
            self._last_size_m = None
            self._last_count = 0
            self._update_all_labels(clear=True)
            return
 
        purposes = [
            UsdGeom.Tokens.default_,
            UsdGeom.Tokens.render,
            UsdGeom.Tokens.proxy,
            UsdGeom.Tokens.guide,
        ]
        bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), purposes, useExtentsHint=True)
 
        union_aabb_stage = None
        count = 0
 
        for p in paths:
            prim = stage.GetPrimAtPath(p)
            if not prim or not prim.IsValid():
                continue
            try:
                # 先取 world bound，再取世界座標軸對齊 AABB
                bbox = bbox_cache.ComputeWorldBound(prim)
                world_aabb = bbox.ComputeAlignedBox()  # Gf.Range3d in stage units
 
                if world_aabb.IsEmpty():
                    continue
 
                if union_aabb_stage is None:
                    union_aabb_stage = Gf.Range3d(world_aabb)
                else:
                    union_aabb_stage.UnionWith(world_aabb)
 
                count += 1
            except Exception:
                continue
 
        if not union_aabb_stage or union_aabb_stage.IsEmpty() or count == 0:
            self._last_size_m = None
            self._last_count = 0
            self._update_all_labels(clear=True)
            return
 
        size_stage = union_aabb_stage.GetSize()  # Vec3d in stage units
        s = float(self._stage_mpu)               # metersPerUnit
        size_m = (float(size_stage[0]) * s, float(size_stage[1]) * s, float(size_stage[2]) * s)
 
        self._last_size_m = size_m
        self._last_count = count
        self._update_all_labels()
 
    def _on_clear(self):
        self._last_size_m = None
        self._last_count = 0
        self._update_all_labels(clear=True)
        self._render_selected_paths([])
 
    # ---------------- display ----------------
    def _fmt(self, meters_value: float) -> float:
        return meters_value / self._display_mpu if self._display_mpu > 0 else meters_value
 
    def _precision_by_unit(self, unit_name: str) -> int:
        return {"mm": 1, "cm": 2, "m": 4, "inch": 2, "ft": 3}.get(unit_name, 3)
 
    def _update_all_labels(self, clear=False):
        if clear or self._last_size_m is None:
            self._len_label.text = "X length: --"
            self._wid_label.text = "Y width : --"
            self._hei_label.text = "Z height: --"
            return
 
        p = self._precision_by_unit(self._display_unit)
        x = self._fmt(self._last_size_m[0])
        y = self._fmt(self._last_size_m[1])
        z = self._fmt(self._last_size_m[2])
 
        self._len_label.text = f"X length: {x:.{p}f} {self._display_unit}"
        self._wid_label.text = f"Y width : {y:.{p}f} {self._display_unit}"
        self._hei_label.text = f"Z height: {z:.{p}f} {self._display_unit}"
 
    # ---------------- helpers ----------------
    def _copy_result(self):
        if not clipboard:
            return
        txt = f"{self._len_label.text}\n{self._wid_label.text}\n{self._hei_label.text}"
        clipboard.copy(txt)