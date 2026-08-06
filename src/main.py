# Kivy Core & App Management
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.stencilview import StencilView
from kivy.graphics import Color, Rectangle, Line, Ellipse, StencilPush, StencilUse, StencilUnUse, StencilPop
from kivy.uix.scatter import Scatter
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.storage.jsonstore import JsonStore
from kivy.utils import platform
from kivy.animation import Animation
try:
    from plyer import vibrator
except ImportError:
    vibrator = None

# Kivy Layouts & Basic UI Widgets
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.effectwidget import EffectWidget, EffectBase
from kivy.uix.spinner import Spinner
from kivy.uix.modalview import ModalView

# Kivy Multimedia & Metrics
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.core.audio import SoundLoader
from kivy.metrics import dp  # <-- FIXED: This stops the 'dp' NameError!

# Kivy Canvas Graphics
from kivy.graphics import RenderContext, Color, Rectangle, Line, Mesh, Ellipse
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import PushMatrix, PopMatrix, Rotate
#from kivy.graphics.rendercontext import RenderContext
#from kivy.graphics.fbo import Fbo
from kivy.graphics.texture import Texture

# Python Native Standard Libraries
import math
import random
import os
import time
from collections import deque
import sys
import json
import asyncio
from datetime import datetime

from kivy.factory import Factory
from scaling import Scale
Factory.register('Scale', cls=Scale)

from kivy.properties import StringProperty

# Web assembly check
IS_WEB = sys.platform == "emscripten"
if IS_WEB:
    from platform import window
    
def get_shared_data_path() -> str:
    """Returns a shared path accessible by both CASINO ARCADE and JBRCADE."""
    if platform == 'android':
        from jnius import autoclass
        Environment = autoclass('android.os.Environment')
        base_dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS).getAbsolutePath()
        shared_dir = os.path.join(base_dir, "JBRCADE")
    else:
        # PC Fallback: Home directory shared folder
        shared_dir = os.path.join(os.path.expanduser("~"), ".arcade_shared_data")
    
    os.makedirs(shared_dir, exist_ok=True)
    return os.path.join(shared_dir, "jbrcade_shared_data.json")

def record_jbrcade_game_score(game_id: str, score: int):
    """Call this on game-over in JBRCADE games to post scores for Casino Arcade."""
    shared_path = get_shared_data_path()
    data = {}
    try:
        if os.path.exists(shared_path):
            with open(shared_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
    except Exception:
        data = {}

    game_scores = data.get('game_scores', {})
    current_best = game_scores.get(game_id, 0)
    
    # Update total accumulated score or high score
    game_scores[game_id] = max(current_best, score)
    data['game_scores'] = game_scores

    try:
        with open(shared_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Failed to record JBRCADE shared score: {e}")

# Place this near the top of main.py (below web_load_game_data / trigger_haptic_feedback)
def apply_theme_background(screen):
    """Updates background color, header banner color, text colors, and seasonal badges."""
    '''app = App.get_running_app()
    if not app:
        return'''
    app = App.get_running_app()
    if app:
        app.update_active_atlas_prefix()

    is_christmas = app.is_christmas_active() if hasattr(app, 'is_christmas_active') else False
    is_halloween = app.is_halloween_active() if hasattr(app, 'is_halloween_active') and not is_christmas else False

    # --- 1. DETERMINE THEME COLORS ---
    if is_christmas:
        bg_color = app.get_primary_bg_color()   # Classic Dark Blue (#0A0F2C)
        border_color = (0.75, 0.1, 0.1, 1)      # Deep Red (Borders)
        text_color = (0.1, 0.55, 0.2, 1)        # Pine Green (Text)
        banner_color = (0.75, 0.85, 1.0, 1)     # Frosty White-Blue (Header & Line)
    elif is_halloween:
        bg_color = (0.12, 0.04, 0.22, 1)        # Spooky Purple
        border_color = (1.0, 0.5, 0.0, 1)      # Pumpkin Orange
        text_color = (1.0, 0.5, 0.0, 1)        # Pumpkin Orange
        banner_color = (1.0, 0.5, 0.0, 1)      # Pumpkin Orange
    else:
        bg_color = app.get_primary_bg_color()   # Classic Dark Blue
        border_color = app.get_accent_color()   # Arcade Cyan
        text_color = app.get_accent_color()     # Arcade Cyan
        banner_color = app.get_accent_color()   # Arcade Cyan

    # --- 2. UPDATE SCREEN BACKGROUND ---
    target_canvas = screen.canvas.before
    if screen.children:
        target_canvas = screen.children[0].canvas.before

    found_color = None
    found_rect = None

    for instr in target_canvas.children:
        if isinstance(instr, Color) and not found_color:
            found_color = instr
        elif isinstance(instr, Rectangle) and not found_rect:
            found_rect = instr

    if not found_color or not found_rect:
        with target_canvas:
            found_color = Color(*bg_color)
            found_rect = Rectangle(pos=screen.pos, size=screen.size)

    found_color.rgb = bg_color[:3]
    found_rect.pos = screen.pos
    found_rect.size = screen.size

    # --- 3. MAIN MENU SPECIFIC THEMING & ACCENT LINES ---
    if screen.name == 'menu':
        # Retrieve header banner widget instance safely from screen.ids
        header_banner_widget = screen.ids.get('header_banner_bg')

        # Repaint Header Banner Background & Line Accents
        if header_banner_widget and hasattr(header_banner_widget, 'canvas') and header_banner_widget.canvas.before:
            children = header_banner_widget.canvas.before.children
            for i, instr in enumerate(children):
                if isinstance(instr, Color):
                    # Look ahead through remaining instructions to see if this Color drives a Rectangle or a Line
                    is_line_color = False
                    for j in range(i + 1, len(children)):
                        if isinstance(children[j], Line):
                            is_line_color = True
                            break
                        elif isinstance(children[j], Rectangle) or isinstance(children[j], Color):
                            break
                    
                    if is_line_color:
                        instr.rgb = banner_color[:3]  # Accent divider line gets banner_color (Cyan/Orange/Frosty)
                    else:
                        instr.rgb = bg_color[:3]      # Banner background gets dark primary color

        def theme_widget_tree(widget):
            # A) Update Text Labels
            if isinstance(widget, Label):
                if "WIND DOWN" not in widget.text:
                    # Title gets banner_color (Frosty White-Blue during Christmas)
                    if "JBRCADE" in widget.text or (header_banner_widget and widget in header_banner_widget.children):
                        widget.color = banner_color
                    else:
                        widget.color = text_color

            # B) Theme Canvas Lines / Tile Borders
            if hasattr(widget, 'canvas') and widget.canvas.before:
                # Skip the header banner widget so its divider line isn't overwritten as a tile border
                if widget != header_banner_widget:
                    children = widget.canvas.before.children
                    for i, instr in enumerate(children):
                        if isinstance(instr, Line):
                            # Look backward through instructions to find driving Color
                            for j in range(i - 1, -1, -1):
                                if isinstance(children[j], Color):
                                    children[j].rgb = border_color[:3]
                                    break

            # Recurse through all child nodes
            if hasattr(widget, 'children') and widget.children:
                for child in widget.children:
                    theme_widget_tree(child)

        theme_widget_tree(screen)

        # C) Attach Seasonal Badges to Active Seasonal Tiles
        if is_halloween and 'halloween_game_preview_button' in screen.ids:
            btn = screen.ids.halloween_game_preview_button
            
            def update_badge_position(instance, value):
                btn.canvas.after.clear()
                if btn.width <= 1 or btn.height <= 1:
                    return
                    
                with btn.canvas.after:
                    Color(1, 1, 1, 1)
                    badge_sz = Scale.min_dim(0.06)
                    Rectangle(
                        source='atlas://assets/images/game_sprites/halloween_badge',
                        pos=(btn.right - badge_sz - dp(4) + 10, btn.top - badge_sz - dp(4) + 10),
                        size=(badge_sz, badge_sz)
                    )

            btn.unbind(pos=update_badge_position, size=update_badge_position)
            btn.bind(pos=update_badge_position, size=update_badge_position)
            Clock.schedule_once(lambda dt: update_badge_position(btn, None), 0.05)

        # 🟢 ADDED: Christmas Badge Binding for Sleigh Drop Tile
        if is_christmas and 'christmas_game_preview_button' in screen.ids:
            btn = screen.ids.christmas_game_preview_button
            
            def update_christmas_badge_position(instance, value):
                btn.canvas.after.clear()
                if btn.width <= 1 or btn.height <= 1:
                    return
                    
                with btn.canvas.after:
                    Color(1, 1, 1, 1)
                    badge_sz = Scale.min_dim(0.06)
                    Rectangle(
                        source='atlas://assets/images/game_sprites/christmas_badge',
                        pos=(btn.right - badge_sz - dp(4) + 10, btn.top - badge_sz - dp(4) + 10),
                        size=(badge_sz, badge_sz)
                    )

            btn.unbind(pos=update_christmas_badge_position, size=update_christmas_badge_position)
            btn.bind(pos=update_christmas_badge_position, size=update_christmas_badge_position)
            Clock.schedule_once(lambda dt: update_christmas_badge_position(btn, None), 0.05)

def web_load_game_data(key_name, default_val=0):
    """Loads save data from browser LocalStorage or local JSON file."""
    if IS_WEB:
        try:
            val = window.localStorage.getItem('jbrcade_save_data')
            if val:
                return json.loads(val).get(key_name, default_val)
        except Exception:
            pass
        return default_val
    else:
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r', encoding='utf-8') as f:
                    return json.load(f).get(key_name, default_val)
        except Exception:
            pass
        return default_val

def web_save_game_data(key_name, value):
    """Saves game data into browser LocalStorage or local JSON file."""
    if IS_WEB:
        try:
            val = window.localStorage.getItem('jbrcade_save_data')
            data = json.loads(val) if val else {}
            data[key_name] = value
            window.localStorage.setItem('jbrcade_save_data', json.dumps(data))
        except Exception:
            pass
    else:
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
            data[key_name] = value
            with open('save_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception:
            pass

def trigger_haptic_feedback(duration=0.08):
    """Triggers vibration on Android (using native PyJNIus), or a desktop tone fallback."""
    app = App.get_running_app()
    
    # Respect user setting (defaults to True)
    if app and hasattr(app, 'haptics_enabled') and not app.haptics_enabled:
        return

    if platform == 'android':
        try:
            from jnius import autoclass
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            Build = autoclass('android.os.Build')

            activity = PythonActivity.mActivity
            vibrator = activity.getSystemService(Context.VIBRATOR_SERVICE)

            if vibrator and vibrator.hasVibrator():
                millis = int(duration * 1000)
                
                # Android 8.0+ (Oreo API 26+) requires VibrationEffect
                if Build.VERSION.SDK_INT >= 26:
                    VibrationEffect = autoclass('android.os.VibrationEffect')
                    effect = VibrationEffect.createOneShot(millis, VibrationEffect.DEFAULT_AMPLITUDE)
                    vibrator.vibrate(effect)
                else:
                    # Deprecated fallback for older Android devices
                    vibrator.vibrate(millis)
        except Exception as e:
            # Fallback to Plyer if PyJNIus fails
            try:
                from plyer import vibrator
                vibrator.vibrate(time=duration)
            except Exception:
                pass

    elif platform == 'win':
        try:
            import winsound
            winsound.Beep(500, int(duration * 1000))
        except Exception:
            print('\a', end='', flush=True)
    else:
        print('\a', end='', flush=True)

class InstructionOverlay(RelativeLayout):
    def __init__(self, game_name, rules_list, close_callback, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.8, 0.6)
        self.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        self.close_callback = close_callback

        # 1. Dark Blue Background Canvas Layer with Bright Blue Border
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)  # #0A0F2C Dark Blue
            self.bg = Rectangle(pos=(0, 0), size=self.size)
            Color(0, 0.75, 1, 1)  # Arcade Bright Blue
            self.border = Line(rectangle=(0, 0, self.width, self.height), width=dp(2))
        
        self.bind(size=self.sync_geometry, pos=self.sync_geometry)

        # 2. Layout Structure Stack
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        self.add_widget(content)

        # Header Title
        content.add_widget(Label(
            text=f"HOW TO PLAY\n{game_name.upper()}", font_name='assets/fonts/ARCADE_N.TTF',
            font_size='14sp', color=(0, 0.75, 1, 1), halign='center', size_hint_y=0.2
        ))

        # Bullet Points Section
        bullets_box = BoxLayout(orientation='vertical', spacing=dp(8), size_hint_y=0.6)
        for rule in rules_list:
            bullets_box.add_widget(Label(
                text=f"* {rule}", font_name='assets/fonts/ARCADE_N.TTF',
                font_size='9sp', color=(1, 1, 1, 1), halign='left', valign='middle',
                text_size=(Window.width * 0.7, None)
            ))
        content.add_widget(bullets_box)

        # Ready Close Action Button
        ready_btn = Button(
            text="READY!", font_name='assets/fonts/ARCADE_N.TTF', font_size='12sp',
            color=(0.04, 0.06, 0.17, 1), background_normal='', background_color=(0, 0.75, 1, 1),
            size_hint=(0.6, 0.18), pos_hint={'center_x': 0.5}
        )
        ready_btn.bind(on_release=self.close_overlay)
        content.add_widget(ready_btn)

    def sync_geometry(self, instance, value):
        self.bg.size = instance.size
        self.border.rectangle = (0, 0, instance.width, instance.height)

    def close_overlay(self, instance):
        if self.parent:
            self.parent.remove_widget(self)
        if self.close_callback:
            self.close_callback()

class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pre_mute_volume = 0.5
        self.is_muted = False
        self.tracks = ['CLASSIC', 'HARDCORE', 'CHILL', 'HALLOWEEN']
        self.cb_modes = ['NONE', 'PROTANOPIA', 'DEUTERANOPIA', 'TRITANOPIA', 'MONOCHROME']

        # 1. Base Layout
        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        # 2. Dynamic Canvas Background (Managed in Python)
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        # 3. Pinned Header
        self.title_label = Label(
            text="SETTINGS",
            font_name='assets/fonts/ARCADE_N.TTF',
            font_size='22sp',
            color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.5, 'top': 0.96},
            size_hint=(1, 0.08)
        )
        self.layout.add_widget(self.title_label)

        # 4. Back Button
        self.back_btn = Button(
            text="< MENU",
            font_name='assets/fonts/ARCADE_N.TTF',
            font_size='10sp',
            color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05),
            pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='',
            background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        # 5. Scrollable Options List
        self.scroll_view = ScrollView(
            size_hint=(0.9, 0.82),
            pos_hint={'center_x': 0.5, 'top': 0.86},
            do_scroll_x=False,
            do_scroll_y=True
        )
        self.layout.add_widget(self.scroll_view)

        self.options_box = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(15),
            padding=[0, dp(10), 0, dp(20)]
        )
        self.options_box.bind(minimum_height=self.options_box.setter('height'))
        self.scroll_view.add_widget(self.options_box)

        # --- OPTION 1: Seasonal UI Toggle Button ---
        self.seasonal_btn = Button(
            text="SEASONAL UI: ON",
            font_name='assets/fonts/ARCADE_N.TTF',
            font_size='12sp',
            size_hint_y=None,
            height=dp(45),
            background_normal='',
            background_color=(0.1, 0.6, 0.3, 1)
        )
        self.seasonal_btn.bind(on_release=lambda x: self.toggle_seasonal_ui())
        self.options_box.add_widget(self.seasonal_btn)

        # --- OPTION 2: Volume Controls ---
        self.vol_label = Label(
            text="VOLUME: 50%",
            font_name='assets/fonts/ARCADE_N.TTF',
            font_size='12sp',
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(25)
        )
        self.options_box.add_widget(self.vol_label)

        vol_btn_row = BoxLayout(orientation='horizontal', spacing=dp(15), size_hint_y=None, height=dp(45))
        minus_btn = Button(text="-", font_name='assets/fonts/ARCADE_N.TTF', font_size='16sp', background_normal='', background_color=(0, 0.5, 0.8, 1))
        minus_btn.bind(on_release=lambda x: self.adjust_volume(-0.05))
        plus_btn = Button(text="+", font_name='assets/fonts/ARCADE_N.TTF', font_size='16sp', background_normal='', background_color=(0, 0.5, 0.8, 1))
        plus_btn.bind(on_release=lambda x: self.adjust_volume(0.05))
        vol_btn_row.add_widget(minus_btn)
        vol_btn_row.add_widget(plus_btn)
        self.options_box.add_widget(vol_btn_row)

        self.mute_btn = Button(
            text="MUTE AUDIO", font_name='assets/fonts/ARCADE_N.TTF', font_size='12sp',
            size_hint_y=None, height=dp(45), background_normal='', background_color=(0.8, 0.2, 0.2, 1)
        )
        self.mute_btn.bind(on_release=lambda x: self.toggle_mute_state())
        self.options_box.add_widget(self.mute_btn)

        # --- OPTION 3: Background Music Track ---
        self.options_box.add_widget(Label(
            text="BACKGROUND MUSIC", font_name='assets/fonts/ARCADE_N.TTF', font_size='12sp',
            color=(0, 0.75, 1, 1), size_hint_y=None, height=dp(25)
        ))
        music_row = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(45))
        prev_music = Button(text="<", font_name='assets/fonts/ARCADE_N.TTF', font_size='12sp', size_hint_x=0.2, background_normal='', background_color=(0, 0.75, 1, 0.3), color=(0, 0.75, 1, 1))
        prev_music.bind(on_release=lambda x: self.cycle_music(-1))
        self.music_label = Label(text="CLASSIC", font_name='assets/fonts/ARCADE_N.TTF', font_size='12sp', color=(1, 1, 1, 1))
        next_music = Button(text=">", font_name='assets/fonts/ARCADE_N.TTF', font_size='12sp', size_hint_x=0.2, background_normal='', background_color=(0, 0.75, 1, 0.3), color=(0, 0.75, 1, 1))
        next_music.bind(on_release=lambda x: self.cycle_music(1))
        music_row.add_widget(prev_music)
        music_row.add_widget(self.music_label)
        music_row.add_widget(next_music)
        self.options_box.add_widget(music_row)

        # --- OPTION 4: Haptics Toggle ---
        self.haptic_btn = Button(
            text="HAPTICS: ON", font_name='assets/fonts/ARCADE_N.TTF', font_size='12sp',
            size_hint_y=None, height=dp(45), background_normal='', background_color=(0.1, 0.6, 0.3, 1)
        )
        self.haptic_btn.bind(on_release=lambda x: self.toggle_haptics_state())
        self.options_box.add_widget(self.haptic_btn)

        # --- OPTION 5: Reset Save Data ---
        self.reset_btn = Button(
            text="RESET SAVE DATA", font_name='assets/fonts/ARCADE_N.TTF', font_size='12sp',
            size_hint_y=None, height=dp(45), background_normal='', background_color=(0.8, 0.2, 0.2, 1)
        )
        self.reset_btn.bind(on_release=lambda x: self.reset_save_data())
        self.options_box.add_widget(self.reset_btn)

        # --- OPTION 6: Color Blindness ---
        self.options_box.add_widget(Label(
            text="COLOR BLINDNESS", font_name='assets/fonts/ARCADE_N.TTF', font_size='12sp',
            color=(0, 0.75, 1, 1), size_hint_y=None, height=dp(25)
        ))
        cb_row = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(45))
        prev_cb = Button(text="<", font_name='assets/fonts/ARCADE_N.TTF', font_size='12sp', size_hint_x=0.2, background_normal='', background_color=(0, 0.75, 1, 0.3), color=(0, 0.75, 1, 1))
        prev_cb.bind(on_release=lambda x: self.cycle_color_blindness(-1))
        self.cb_label = Label(text="NONE", font_name='assets/fonts/ARCADE_N.TTF', font_size='12sp', color=(1, 1, 1, 1))
        next_cb = Button(text=">", font_name='assets/fonts/ARCADE_N.TTF', font_size='12sp', size_hint_x=0.2, background_normal='', background_color=(0, 0.75, 1, 0.3), color=(0, 0.75, 1, 1))
        next_cb.bind(on_release=lambda x: self.cycle_color_blindness(1))
        cb_row.add_widget(prev_cb)
        cb_row.add_widget(self.cb_label)
        cb_row.add_widget(next_cb)
        self.options_box.add_widget(cb_row)
        
    def get_available_tracks(self):
        """Returns active tracks depending on whether Halloween or Christmas mode is active."""
        app = App.get_running_app()
        tracks = ['CLASSIC', 'HARDCORE', 'CHILL']
        if app:
            if app.is_halloween_active():
                tracks.append('HALLOWEEN')
            if app.is_christmas_active():
                tracks.append('CHRISTMAS')
        return tracks

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        apply_theme_background(self)

    def go_back_to_menu(self, instance):
        self.manager.current = 'menu'

    def on_pre_enter(self, *args):
        apply_theme_background(self)
        self.sync_ui_with_app_state()

    def sync_ui_with_app_state(self):
        app = App.get_running_app()
        if not app: return

        if app.bg_track:
            if app.is_muted or app.bg_track.volume == 0:
                self.vol_label.text = "VOLUME: MUTED"
                self.mute_btn.text = "UNMUTE AUDIO"
                self.mute_btn.background_color = (0.1, 0.6, 0.3, 1)
            else:
                vol_pct = int(round(app.bg_track.volume * 100))
                self.vol_label.text = f"VOLUME: {vol_pct}%"
                self.mute_btn.text = "MUTE AUDIO"
                self.mute_btn.background_color = (0.8, 0.2, 0.2, 1)

        if app.haptics_enabled:
            self.haptic_btn.text = "HAPTICS: ON"
            self.haptic_btn.background_color = (0.1, 0.6, 0.3, 1)
        else:
            self.haptic_btn.text = "HAPTICS: OFF"
            self.haptic_btn.background_color = (0.8, 0.2, 0.2, 1)

        self.music_label.text = app.current_music_name
        self.cb_label.text = app.color_blind_mode
            
        if app.seasonal_ui_enabled:
            self.seasonal_btn.text = "SEASONAL UI: ON"
            self.seasonal_btn.background_color = (0.1, 0.6, 0.3, 1)
        else:
            self.seasonal_btn.text = "SEASONAL UI: OFF"
            self.seasonal_btn.background_color = (0.8, 0.2, 0.2, 1)

    def toggle_seasonal_ui(self):
        app = App.get_running_app()
        app.seasonal_ui_enabled = not app.seasonal_ui_enabled
        app.save_seasonal_settings()

        # Revert track to CLASSIC if seasonal UI is turned off while playing a seasonal song
        if not app.seasonal_ui_enabled and app.current_music_name in ['CHRISTMAS', 'HALLOWEEN']:
            app.switch_music_track('CLASSIC')

        # Re-apply theme background across current and main menu screens
        apply_theme_background(self)
        if app.sm and app.sm.has_screen('menu'):
            apply_theme_background(app.sm.get_screen('menu'))

        self.sync_ui_with_app_state()
        trigger_haptic_feedback(0.08)

    def cycle_color_blindness(self, direction):
        app = App.get_running_app()
        current_idx = self.cb_modes.index(app.color_blind_mode)
        new_idx = (current_idx + direction) % len(self.cb_modes)
        new_mode = self.cb_modes[new_idx]
        
        app.save_color_blind_setting(new_mode)
        self.cb_label.text = new_mode  # 🟢 FIXED: Reference self.cb_label directly
        app.apply_color_blind_filter(new_mode)

    def cycle_music(self, direction):
        app = App.get_running_app()
        available_tracks = self.get_available_tracks()
        
        # Fallback if current track isn't in available list
        current_name = app.current_music_name if app.current_music_name in available_tracks else available_tracks[0]
        current_idx = available_tracks.index(current_name)
        
        new_idx = (current_idx + direction) % len(available_tracks)
        new_track_name = available_tracks[new_idx]
        
        app.switch_music_track(new_track_name)
        self.music_label.text = new_track_name

    def toggle_haptics_state(self):
        app = App.get_running_app()
        new_state = not app.haptics_enabled
        app.save_haptics_setting(new_state)

        if new_state:
            self.ids.haptic_btn.text = "HAPTICS: ON"
            self.ids.haptic_btn.background_color = (0.1, 0.6, 0.3, 1)
            trigger_haptic_feedback(0.08)
        else:
            self.ids.haptic_btn.text = "HAPTICS: OFF"
            self.ids.haptic_btn.background_color = (0.8, 0.2, 0.2, 1)

    def adjust_volume(self, delta_modifier):
        app = App.get_running_app()
        if not app.bg_track: return

        app.is_muted = False
        new_vol = max(0.0, min(1.0, app.bg_track.volume + delta_modifier))
        app.bg_track.volume = round(new_vol, 2)
        app.save_audio_settings()
        
        self.sync_ui_with_app_state()

    def toggle_mute_state(self):
        app = App.get_running_app()
        if not app or not app.bg_track: 
            return

        if not app.is_muted:
            self.pre_mute_volume = app.bg_track.volume if app.bg_track.volume > 0 else 0.5
            app.bg_track.volume = 0.0
            app.is_muted = True
        else:
            app.bg_track.volume = self.pre_mute_volume
            app.is_muted = False

        app.save_audio_settings()
        self.sync_ui_with_app_state()

    def reset_save_data(self):
        try:
            # 1. Remove save_data.json on disk
            if os.path.exists('save_data.json'):
                os.remove('save_data.json')

            # 2. Mechanically reset app preferences to defaults
            app = App.get_running_app()
            if app:
                app.color_blind_mode = 'NONE'
                app.haptics_enabled = True
                app.is_muted = False
                
                # Reset music track to CLASSIC
                app.switch_music_track('CLASSIC')
                if app.bg_track:
                    app.bg_track.volume = 0.5
                app.apply_color_blind_filter('NONE')

                # Reset high scores in all screen instances
                if app.sm:
                    for screen in app.sm.screens:
                        if hasattr(screen, 'high_score'):
                            screen.high_score = 1 if screen.name in ['focus_flash', 'planet_hopper', 'air_traffic', 'rotational_maze'] else 0
                        if hasattr(screen, 'load_high_score'):
                            screen.load_high_score()
                        if hasattr(screen, 'update_difficulty_ui'):
                            screen.update_difficulty_ui()

            # 3. Visually revert all Settings screen buttons/labels
            self.sync_ui_with_app_state()

            # 4. Trigger feedback button text
            trigger_haptic_feedback(0.12)
            if hasattr(self.ids, 'reset_btn'):
                self.ids.reset_btn.text = "DATA CLEARED!"
                Clock.schedule_once(lambda dt: setattr(self.ids.reset_btn, 'text', "RESET SAVE DATA"), 2.0)
        except Exception:
            pass

class AboutScreen(Screen):
    # 🟢 FIXED RESET LIFE-CYCLE: Ensures the screen state refreshes safely on entry transitions
    def on_pre_enter(self, *args):
        pass
    
class AchievementsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        # 1. Background
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        # 2. Header
        self.title_label = Label(
            text="ACHIEVEMENTS",
            font_name='assets/fonts/ARCADE_N.TTF',
            font_size=Scale.font(18),
            color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.5, 'top': 0.95},
            size_hint=(1, 0.08)
        )
        self.layout.add_widget(self.title_label)

        # 3. Back Button
        self.back_btn = Button(
            text="< MENU",
            font_name='assets/fonts/ARCADE_N.TTF',
            font_size=Scale.font(15),
            size_hint=(0.25, 0.05),
            pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='',
            background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        # 4. Scrollable Container for Achievement List
        self.scroll_view = ScrollView(
            size_hint=(0.95, 0.82),
            pos_hint={'center_x': 0.5, 'top': 0.85},
            do_scroll_x=False,
            do_scroll_y=True
        )
        self.layout.add_widget(self.scroll_view)

        self.list_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(12),
            padding=[0, dp(10), 0, dp(10)]
        )
        self.list_container.bind(minimum_height=self.list_container.setter('height'))
        self.scroll_view.add_widget(self.list_container)

        # Defined Achievements Registry with Atlas Sprite Paths
        self.achievements_data = [
            {
                'id': 'toasty_normal_15',
                'title': 'LIGHTLY TOASTED',
                'desc': 'Score 10 points in Toasty Mallow (Normal Mode).',
                'sprite': 'atlas://assets/images/game_sprites/toasty_normal_15'
            },
            {
                'id': 'toasty_normal_50',
                'title': 'MALLOW MASTER',
                'desc': 'Score 50 points in Toasty Mallow (Normal Mode).',
                'sprite': 'atlas://assets/images/game_sprites/toasty_normal_50'
            },
            {
                'id': 'toasty_normal_100',
                'title': 'UNTOASTABLE',
                'desc': 'Score 100 points in Toasty Mallow (Normal Mode).',
                'sprite': 'atlas://assets/images/game_sprites/toasty_normal_100'
            },
            {
                'id': 'gatekeeper_flawless_3',
                'title': 'LUNAR SHIELD',
                'desc': 'Complete 3 rounds of Gate Keeper without making any mistakes.',
                'sprite': 'atlas://assets/images/game_sprites/gatekeeper_flawless_3'
            },
            {
                'id': 'gatekeeper_flawless_6',
                'title': 'CELESTIAL BULWARK',
                'desc': 'Complete 6 rounds of Gate Keeper without making any mistakes.',
                'sprite': 'atlas://assets/images/game_sprites/gatekeeper_flawless_6'
            },
            {
                'id': 'gatekeeper_flawless_9',
                'title': 'INFINITUM AEGIS',
                'desc': 'Complete 9 rounds of Gate Keeper without making any mistakes.',
                'sprite': 'atlas://assets/images/game_sprites/gatekeeper_flawless_9'
            },
        ]

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def on_pre_enter(self, *args):
        self.render_achievements_list()

    def go_back_to_menu(self, instance):
        self.manager.current = 'menu'

    def get_unlocked_dict(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('achievements', {})
        except Exception:
            pass
        return {}

    def render_achievements_list(self):
        self.list_container.clear_widgets()
        unlocked_map = self.get_unlocked_dict()

        row_height = Scale.min_dim(0.22)
        tile_dim = Scale.min_dim(0.18)

        for ach in self.achievements_data:
            is_unlocked = unlocked_map.get(ach['id'], False)

            # Row Layout
            row = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=row_height,
                spacing=dp(12),
                padding=[dp(8), 0, dp(8), 0]
            )

            # Left: Icon Tile Box
            tile_box = RelativeLayout(size_hint=(None, 1), width=tile_dim)
            
            with tile_box.canvas.before:
                if is_unlocked:
                    # Renders full atlas texture image when unlocked
                    Color(1, 1, 1, 1)
                    Rectangle(
                        source=ach['sprite'],
                        pos=(0, (row_height - tile_dim) / 2),
                        size=(tile_dim, tile_dim)
                    )
                else:
                    # Dark silhouette tile when locked
                    Color(0.1, 0.12, 0.22, 1)
                    Rectangle(
                        pos=(0, (row_height - tile_dim) / 2),
                        size=(tile_dim, tile_dim)
                    )

                # Tile Border
                Color(0, 0.75, 1, 1) if is_unlocked else Color(0.3, 0.3, 0.4, 0.6)
                Line(
                    rectangle=(0, (row_height - tile_dim) / 2, tile_dim, tile_dim),
                    width=dp(2)
                )

            row.add_widget(tile_box)

            # Right: Text Details Column
            text_box = BoxLayout(orientation='vertical', spacing=dp(4))
            
            title_lbl = Label(
                text=ach['title'] if is_unlocked else "??? LOCKED ???",
                font_name='assets/fonts/ARCADE_N.TTF',
                font_size=Scale.font(12),
                color=(1, 0.84, 0, 1) if is_unlocked else (0.5, 0.5, 0.6, 1),
                halign='left',
                valign='bottom',
                size_hint_y=0.45
            )
            title_lbl.bind(size=title_lbl.setter('text_size'))

            desc_lbl = Label(
                text=ach['desc'],
                font_name='assets/fonts/ARCADE_N.TTF',
                font_size=Scale.font(8),
                color=(1, 1, 1, 1) if is_unlocked else (0.4, 0.4, 0.5, 1),
                halign='left',
                valign='top',
                size_hint_y=0.55
            )
            desc_lbl.bind(size=desc_lbl.setter('text_size'))

            text_box.add_widget(title_lbl)
            text_box.add_widget(desc_lbl)
            row.add_widget(text_box)

            self.list_container.add_widget(row)

class MainMenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tap_count = 0
        self.reset_event = None
        self.pause_event = None

        # Particle Engine Setup
        self.particles = []
        self.particle_event = None
        self.glow_anim = None
        
    def sync_seasonal_tiles(self):
        app = App.get_running_app()
        is_halloween = app and app.is_halloween_active()
        is_christmas = app and app.is_christmas_active()

        # Halloween Preview Tile
        if 'halloween_game_tile_container' in self.ids:
            container = self.ids.halloween_game_tile_container
            btn = self.ids.halloween_game_preview_button

            if is_halloween:
                container.opacity = 1
                container.disabled = False
                btn.disabled = False
            else:
                container.opacity = 0
                container.disabled = True
                btn.disabled = True

        # Christmas Preview Tile (Sleigh Drop)
        if 'christmas_game_tile_container' in self.ids:
            container = self.ids.christmas_game_tile_container
            btn = self.ids.christmas_game_preview_button

            if is_christmas:
                container.opacity = 1
                container.disabled = False
                btn.disabled = False
            else:
                container.opacity = 0
                container.disabled = True
                btn.disabled = True

    def on_pre_enter(self, *args):
        apply_theme_background(self)
        self.sync_seasonal_tiles()
        self.start_seasonal_effects()

    def on_leave(self, *args):
        self.stop_seasonal_effects()

    def start_seasonal_effects(self):
        app = App.get_running_app()
        if not app:
            self.stop_seasonal_effects()
            return

        is_christmas = getattr(app, 'is_christmas_active', lambda: False)()
        is_halloween = getattr(app, 'is_halloween_active', lambda: False)()

        # If no seasonal mode is active, ensure all effects are stopped
        if not is_christmas and not is_halloween:
            self.stop_seasonal_effects()
            return

        # 1. Pulsing Header Glow (HALLOWEEN ONLY)
        if is_halloween and 'jbrcade_title_label' in self.ids and not self.glow_anim:
            lbl = self.ids.jbrcade_title_label
            glow_color = (1.0, 0.65, 0.1, 1.0)
            dim_color = (1.0, 0.35, 0.0, 0.8)
            
            self.glow_anim = (
                Animation(color=glow_color, duration=1.2, t='in_out_quad') + 
                Animation(color=dim_color, duration=1.2, t='in_out_quad')
            )
            self.glow_anim.repeat = True
            self.glow_anim.start(lbl)

        # 2. Spawn Floating Particles (Snowflakes vs Embers)
        if not self.particles:
            num_particles = 30 if is_christmas else 20
            for _ in range(num_particles):
                self.particles.append({
                    'x': random.uniform(0, Window.width),
                    'y': random.uniform(0, Window.height),
                    'size': random.uniform(Scale.font(2), Scale.font(6)),
                    'speed_y': -random.uniform(Scale.vel_h(0.5), Scale.vel_h(1.5)) if is_christmas else random.uniform(Scale.vel_h(0.4), Scale.vel_h(1.2)),
                    'speed_x': random.uniform(Scale.vel_w(-0.4), Scale.vel_w(0.4)),
                    'opacity': random.uniform(0.4, 0.9)
                })

        if not self.particle_event:
            self.particle_event = Clock.schedule_interval(self.update_seasonal_particles, 1.0 / 60.0)

    def stop_seasonal_effects(self):
        if self.particle_event:
            Clock.unschedule(self.particle_event)
            self.particle_event = None

        if self.glow_anim and 'jbrcade_title_label' in self.ids:
            self.glow_anim.cancel(self.ids.jbrcade_title_label)
            self.glow_anim = None

        self.canvas.after.remove_group('seasonal_particles')
        self.particles = []

    def update_seasonal_particles(self, dt):
        app = App.get_running_app()
        if not app:
            self.stop_seasonal_effects()
            return

        is_christmas = getattr(app, 'is_christmas_active', lambda: False)()

        self.canvas.after.remove_group('seasonal_particles')
        
        with self.canvas.after:
            for p in self.particles:
                # Drift physics
                p['y'] += p['speed_y'] * (dt * 60.0)
                p['x'] += p['speed_x'] * (dt * 60.0)

                if is_christmas:
                    # Reset snowflake to top boundary when falling off the bottom
                    if p['y'] < -p['size']:
                        p['y'] = Window.height + p['size']
                        p['x'] = random.uniform(0, Window.width)
                    # White Snow particles
                    Color(1.0, 1.0, 1.0, p['opacity'], group='seasonal_particles')
                else:
                    # Reset ember to bottom boundary when drifting past the top
                    if p['y'] > Window.height:
                        p['y'] = -p['size']
                        p['x'] = random.uniform(0, Window.width)
                    # Pumpkin Orange Embers
                    Color(1.0, 0.5, 0.0, p['opacity'], group='seasonal_particles')

                Ellipse(pos=(p['x'], p['y']), size=(p['size'], p['size']), group='seasonal_particles')
                
    def on_touch_down(self, touch):
        # 1. Direct collision check against header banner widget
        hit_banner = False
        if 'header_banner_bg' in self.ids:
            hit_banner = self.ids.header_banner_bg.collide_point(*touch.pos)
        
        # 2. Fallback check: Top 10% of window screen
        is_top_strip = touch.y >= Window.height * 0.90

        if hit_banner or is_top_strip:
            self.register_easter_egg_tap()
            return True  # Consume touch event for easter egg tap chain
            
        return super().on_touch_down(touch)
    
    def register_easter_egg_tap(self):
        # If user taps during the 1-second mandatory pause, fail & reset!
        if self.pause_event:
            Clock.unschedule(self.pause_event)
            self.pause_event = None
            self.tap_count = 0
            trigger_haptic_feedback(0.08)
            return

        # Cancel auto-reset timeout on active tap chain
        if self.reset_event:
            Clock.unschedule(self.reset_event)

        self.tap_count += 1

        if self.tap_count == 13:
            # 13th tap achieved! Schedule mandatory 1.0s pause check
            trigger_haptic_feedback(0.04)
            self.pause_event = Clock.schedule_once(self.unlock_cheat_screen, 1.0)
        else:
            # Reset tap counter if next tap doesn't arrive within 0.6 seconds
            self.reset_event = Clock.schedule_once(self.reset_tap_count, 0.6)

    def reset_tap_count(self, dt):
        self.tap_count = 0
        self.reset_event = None

    def unlock_cheat_screen(self, dt):
        self.pause_event = None
        self.tap_count = 0
        trigger_haptic_feedback(0.2)  # Long haptic buzz for success
        self.manager.current = 'cheats'

class CheatsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.all_unlocked_state = False

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        # 1. Dark Background
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        # 2. Header
        self.title_label = Label(
            text="DEV CHEATS",
            font_name='assets/fonts/ARCADE_N.TTF',
            font_size=Scale.font(18),
            color=(1, 0.84, 0, 1),
            pos_hint={'center_x': 0.5, 'top': 0.95},
            size_hint=(1, 0.08)
        )
        self.layout.add_widget(self.title_label)

        self.subtitle_label = Label(
            text="AUTHORIZED PERSONNEL ONLY!",
            font_name='assets/fonts/ARCADE_N.TTF',
            font_size=Scale.font(8),
            color=(0.7, 0.7, 0.8, 0.8),
            pos_hint={'center_x': 0.5, 'top': 0.88},
            size_hint=(1, 0.05)
        )
        self.layout.add_widget(self.subtitle_label)

        # 3. Back Button
        self.back_btn = Button(
            text="< MENU",
            font_name='assets/fonts/ARCADE_N.TTF',
            font_size=Scale.font(15),
            size_hint=(0.25, 0.05),
            pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='',
            background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back)
        self.layout.add_widget(self.back_btn)

        # 4. Cheats Buttons Stack
        self.cheat_toggle_btn = Button(
            text="ALL ACHIEVEMENTS: OFF",
            font_name='assets/fonts/ARCADE_N.TTF',
            font_size=Scale.font(12),
            size_hint=(0.85, 0.08),
            pos_hint={'center_x': 0.5, 'center_y': 0.65},
            background_normal='',
            background_color=(0.8, 0.2, 0.2, 1)
        )
        self.cheat_toggle_btn.bind(on_release=self.toggle_all_achievements)
        self.layout.add_widget(self.cheat_toggle_btn)
        
        self.halloween_toggle_btn = Button(
            text="DEV HALLOWEEN: OFF",
            font_name='assets/fonts/ARCADE_N.TTF',
            font_size=Scale.font(12),
            size_hint=(0.85, 0.08),
            pos_hint={'center_x': 0.5, 'center_y': 0.52},
            background_normal='',
            background_color=(0.8, 0.2, 0.2, 1)
        )
        self.halloween_toggle_btn.bind(on_release=self.toggle_dev_halloween)
        self.layout.add_widget(self.halloween_toggle_btn)

        # --- NEW: DEV CHRISTMAS TOGGLE ---
        self.christmas_toggle_btn = Button(
            text="DEV CHRISTMAS: OFF",
            font_name='assets/fonts/ARCADE_N.TTF',
            font_size=Scale.font(12),
            size_hint=(0.85, 0.08),
            pos_hint={'center_x': 0.5, 'center_y': 0.39},
            background_normal='',
            background_color=(0.8, 0.2, 0.2, 1)
        )
        self.christmas_toggle_btn.bind(on_release=self.toggle_dev_christmas)
        self.layout.add_widget(self.christmas_toggle_btn)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        apply_theme_background(self)

    def on_pre_enter(self, *args):
        self.sync_cheat_state()

    def go_back(self, instance):
        self.manager.current = 'menu'

    def sync_cheat_state(self):
        app = App.get_running_app()
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    achievements = data.get('achievements', {})
                    # Check if all registered achievements are True
                    self.all_unlocked_state = achievements.get('toasty_normal_15', False)
        except Exception:
            self.all_unlocked_state = False

        self.update_button_ui()
        self.update_halloween_button_ui()
        self.update_christmas_button_ui()
        
    def update_christmas_button_ui(self):
        app = App.get_running_app()
        if app and getattr(app, 'dev_christmas_override', False):
            self.christmas_toggle_btn.text = "DEV CHRISTMAS: ON"
            self.christmas_toggle_btn.background_color = (0.1, 0.6, 0.3, 1)
        else:
            self.christmas_toggle_btn.text = "DEV CHRISTMAS: OFF"
            self.christmas_toggle_btn.background_color = (0.8, 0.2, 0.2, 1)
        
    def update_halloween_button_ui(self):
        app = App.get_running_app()
        if app and app.dev_halloween_override:
            self.halloween_toggle_btn.text = "DEV HALLOWEEN: ON"
            self.halloween_toggle_btn.background_color = (0.1, 0.6, 0.3, 1)
        else:
            self.halloween_toggle_btn.text = "DEV HALLOWEEN: OFF"
            self.halloween_toggle_btn.background_color = (0.8, 0.2, 0.2, 1)
            
    def toggle_dev_christmas(self, instance):
        app = App.get_running_app()
        if app:
            # Toggle Christmas & clear Halloween override
            app.dev_christmas_override = not getattr(app, 'dev_christmas_override', False)
            if app.dev_christmas_override:
                app.dev_halloween_override = False
            
            app.save_seasonal_settings()
            
            # Revert track to CLASSIC if Christmas turned off while playing CHRISTMAS
            if not app.is_christmas_active() and app.current_music_name == 'CHRISTMAS':
                app.switch_music_track('CLASSIC')
                
            self.update_halloween_button_ui()
            self.update_christmas_button_ui()
            trigger_haptic_feedback(0.08)
            
    def toggle_dev_halloween(self, instance):
        app = App.get_running_app()
        if app:
            app.dev_halloween_override = not app.dev_halloween_override
            if app.dev_halloween_override:
                app.dev_christmas_override = False

            app.save_seasonal_settings()
            
            # Revert track to CLASSIC if Halloween turned off while playing HALLOWEEN
            if not app.is_halloween_active() and app.current_music_name == 'HALLOWEEN':
                app.switch_music_track('CLASSIC')
                
            self.update_halloween_button_ui()
            self.update_christmas_button_ui()
            trigger_haptic_feedback(0.08)

    def update_button_ui(self):
        if self.all_unlocked_state:
            self.cheat_toggle_btn.text = "ALL ACHIEVEMENTS: ON"
            self.cheat_toggle_btn.background_color = (0.1, 0.6, 0.3, 1)  # Green
        else:
            self.cheat_toggle_btn.text = "ALL ACHIEVEMENTS: OFF"
            self.cheat_toggle_btn.background_color = (0.8, 0.2, 0.2, 1)  # Red

    def toggle_all_achievements(self, instance):
        self.all_unlocked_state = not self.all_unlocked_state

        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)

            # Set achievement keys according to toggle state
            achievements = {
                'toasty_normal_15': self.all_unlocked_state,
                'toasty_normal_50': self.all_unlocked_state,
                'toasty_normal_100': self.all_unlocked_state,
                'gatekeeper_flawless_3': self.all_unlocked_state,
                'gatekeeper_flawless_6': self.all_unlocked_state,
                'gatekeeper_flawless_9': self.all_unlocked_state
            }
            data['achievements'] = achievements

            with open('save_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f)

            trigger_haptic_feedback(0.08)
        except Exception:
            pass

        self.update_button_ui()

class ToastyMallowScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.game_running = False
        # Physics scaled to screen dimensions via Scale utility
        self.gravity = Scale.vel_h(-0.8)          
        self.velocity = 0 
        self.jump_strength = Scale.vel_h(14.0)      
        self.score = 0 
        self.obstacles = [] 
        
        self.difficulties = ['DREAMY', 'EASY', 'NORMAL', 'HARD', 'NIGHTMARE']
        self.current_diff_idx = 2  # Default to NORMAL
        self.high_score = 0
        
        self.update_event = None 
        self.spawn_event = None 
        self.start_countdown_event = None  # Tracked timer reference
        
        self.stars = [] 
        self.star_scroll_speed = Scale.vel_w(1.0) 
        self.generate_initial_stars() 
        
        self.trail_particles = []
        self.trail_timer = 0.0

        self.layout = RelativeLayout()
        self.add_widget(self.layout)
        
        with self.canvas.before: 
            Color(0.04, 0.06, 0.17, 1) 
            self.bg_rect = Rectangle(pos=self.pos, size=self.size) 
        self.bind(pos=self.update_bg, size=self.update_bg) 

        # UI Headers & Score Displays (Scaled Fonts)
        self.title_label = Label(
            text="TOASTY MALLOW", font_size=Scale.font(30), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.75}
        )
        self.layout.add_widget(self.title_label)
        
        self.score_label = Label(
            text="SCORE: 0  |  BEST: 0", 
            font_size=Scale.font(15), 
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 1, 1, 1), 
            pos_hint={'center_x': 0.5, 'center_y': 0.88},
            opacity=0
        )
        self.layout.add_widget(self.score_label)
        
        self.high_score_alert = Label(
            text="NEW HIGH SCORE!", font_size=Scale.font(16), font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 0.84, 0, 1), pos_hint={'center_x': 0.5, 'center_y': 0.70},
            opacity=0
        )
        self.layout.add_widget(self.high_score_alert)

        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        # Standardized Action Controls Row Wrapper
        self.play_help_row = BoxLayout(
            orientation='horizontal', spacing=dp(10),
            size_hint=(0.9, 0.1), pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(30), font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.75, 1, 1), color=(0.04, 0.06, 0.17, 1),
            size_hint_x=0.8
        )
        self.start_btn.bind(on_release=self.start_game_countdown)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size=Scale.font(16), font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

        # Difficulty Row (Positioned underneath play_help_row at y=0.1)
        self.diff_row = BoxLayout(
            orientation='horizontal', spacing=dp(10), 
            size_hint=(0.9, None), height=dp(45),
            pos_hint={'center_x': 0.5, 'center_y': 0.1}
        )
        self.layout.add_widget(self.diff_row)

        self.prev_diff_btn = Button(
            text="<", font_name='assets/fonts/ARCADE_N.TTF', font_size=Scale.font(16), size_hint_x=0.2,
            background_normal='', background_color=(0, 0.75, 1, 0.3), color=(0, 0.75, 1, 1)
        )
        self.prev_diff_btn.bind(on_release=lambda x: self.cycle_difficulty(-1))
        self.diff_row.add_widget(self.prev_diff_btn)

        self.diff_label = Label(
            text="NORMAL", font_name='assets/fonts/ARCADE_N.TTF', font_size=Scale.font(16),
            color=(1, 1, 1, 1), halign='center'
        )
        self.diff_row.add_widget(self.diff_label)

        self.next_diff_btn = Button(
            text=">", font_name='assets/fonts/ARCADE_N.TTF', font_size=Scale.font(16), size_hint_x=0.2,
            background_normal='', background_color=(0, 0.75, 1, 0.3), color=(0, 0.75, 1, 1)
        )
        self.next_diff_btn.bind(on_release=lambda x: self.cycle_difficulty(1))
        self.diff_row.add_widget(self.next_diff_btn)

        # Mallow Dimensions (Sized using minimum screen dimension to prevent stretching on wide tablets)
        self.mallow_x = Scale.width_pct(0.2) 
        self.mallow_y = Scale.height_pct(0.5) 
        self.mallow_w = Scale.min_dim(0.15) 
        self.mallow_h = Scale.min_dim(0.15) 
        
        self.load_high_score()
        
    # Inside ToastyMallowScreen

    def check_achievements(self):
        mode = self.difficulties[self.current_diff_idx]
        # Check if we hit 10 points on Normal mode
        if mode == 'NORMAL':
            if self.score >= 10:
                self.unlock_achievement('toasty_normal_15')
            if self.score >= 50:
                self.unlock_achievement('toasty_normal_50')
            if self.score >= 100:
                self.unlock_achievement('toasty_normal_100')

    def unlock_achievement(self, achievement_id):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            achievements = data.get('achievements', {})
            if not achievements.get(achievement_id, False):
                achievements[achievement_id] = True
                data['achievements'] = achievements
                
                with open('save_data.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f)
                
                # Trigger haptic feedback for unlock
                trigger_haptic_feedback(0.2)
        except Exception:
            pass

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.diff_row.disabled = True
        self.back_btn.disabled = True
        
        game_name = "Toasty Mallow"
        placeholders = [
            "tap to jump",
            "don't hit the logs, ceiling or floor",
            "switch the difficulty for a more relaxing or exhilarating experience"
        ]
        
        overlay = InstructionOverlay(
            game_name=game_name, 
            rules_list=placeholders, 
            close_callback=self.on_instructions_closed
        )
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.diff_row.disabled = False
        self.back_btn.disabled = False
    
    def on_pre_enter(self, *args):
        self.update_difficulty_ui()

    def on_leave(self, *args):
        self.cleanup_engine()

    def generate_initial_stars(self):
        self.stars = [] 
        for _ in range(30): 
            self.stars.append({ 
                'x': random.uniform(0, Window.width), 
                'y': random.uniform(0, Window.height), 
                'size': random.uniform(Scale.font(2), Scale.font(5)), 
                'opacity': random.uniform(0.3, 0.6) 
            }) 

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos 
        self.bg_rect.size = self.size 
        self.mallow_w = Scale.min_dim(0.15) 
        self.mallow_h = self.mallow_w 
        if not self.game_running: 
            self.mallow_y = Scale.height_pct(0.5) 
        self.draw_game_canvas() 

    def go_back_to_menu(self, instance=None):
        self.game_running = False
        self.cleanup_engine() 
        self.title_label.opacity = 1
        self.title_label.text = "TOASTY MALLOW"
        self.play_help_row.opacity = 1
        self.play_help_row.disabled = False
        self.diff_row.opacity = 1
        self.diff_row.disabled = False
        self.manager.current = 'menu' 

    def cycle_difficulty(self, direction):
        if self.game_running: return
        self.current_diff_idx = (self.current_diff_idx + direction) % len(self.difficulties)
        self.update_difficulty_ui()

    def update_difficulty_ui(self):
        mode = self.difficulties[self.current_diff_idx]
        self.diff_label.text = mode
        self.load_high_score()
        self.score_label.text = f"SCORE: {self.score}  |  BEST: {self.high_score}"
        
        if mode == 'DREAMY': self.diff_label.color = (0, 1, 0.8, 1)
        elif mode == 'EASY': self.diff_label.color = (0.2, 0.8, 0.2, 1)
        elif mode == 'NORMAL': self.diff_label.color = (1, 1, 1, 1)
        elif mode == 'HARD': self.diff_label.color = (1, 0.5, 0, 1)
        elif mode == 'NIGHTMARE': self.diff_label.color = (0.9, 0.1, 0.1, 1)

    def load_high_score(self):
        mode = self.difficulties[self.current_diff_idx].lower()
        # Use web_load_game_data helper so JSON/Web save keys match across screens
        self.high_score = web_load_game_data(f'toasty_mallow_{mode}_high', 0)

    def save_high_score(self):
        mode = self.difficulties[self.current_diff_idx].lower()
        # Use web_save_game_data helper
        web_save_game_data(f'toasty_mallow_{mode}_high', self.high_score)

    def start_game_countdown(self, instance=None):
        self.cleanup_engine() 
        self.score = 0 
        self.mallow_y = Scale.height_pct(0.5) 
        self.velocity = 0 
        self.obstacles = [] 
        
        self.title_label.opacity = 0 
        self.high_score_alert.opacity = 0 
        self.score_label.opacity = 0 
        
        self.play_help_row.opacity = 0
        self.play_help_row.disabled = True
        self.diff_row.opacity = 0
        self.diff_row.disabled = True
        
        self.start_countdown_event = Clock.schedule_once(self.start_game_engine, 1.0) 

    def start_game_engine(self, dt):
        self.start_countdown_event = None
        self.game_running = True 
        self.velocity = 0 
        self.obstacles = [] 
        self.score_label.opacity = 1 
        self.score_label.text = f"SCORE: 0  |  BEST: {self.high_score}"
        
        self.spawn_log_obstacle(0) 
        self.update_event = Clock.schedule_interval(self.update_physics, 1.0 / 60.0) 
        self.spawn_event = Clock.schedule_interval(self.spawn_log_obstacle, 1.5)

    def spawn_log_obstacle(self, dt):
        if not self.game_running: return 
        
        mode = self.difficulties[self.current_diff_idx]
        anim_type = 'STATIC'
        
        if mode == 'DREAMY':
            gap = Scale.height_pct(0.45)   
        elif mode == 'EASY':
            gap = Scale.height_pct(0.37)
        elif mode == 'NORMAL':
            gap = Scale.height_pct(0.28)
        elif mode == 'HARD':
            anim_type = random.choice(['STATIC', 'SHIFT', 'PULSE'])
            gap = Scale.height_pct(0.45) if anim_type == 'PULSE' else Scale.height_pct(0.32)
        elif mode == 'NIGHTMARE':
            gap = Scale.height_pct(0.23)
            
        min_height = Scale.height_pct(0.15) 
        max_height = Scale.height_pct(0.65)
        bottom_log_height = random.uniform(min_height, max_height) 
        top_log_pos_y = bottom_log_height + gap 
        top_log_height = Window.height - top_log_pos_y 
        
        anim_dir = -1 if anim_type == 'PULSE' else random.choice([-1, 1])
        anim_speed = Scale.vel_h(random.uniform(1.0, 2.0))

        self.obstacles.append({
            'x': Window.width, 
            'bottom_h': bottom_log_height, 
            'top_y': top_log_pos_y, 
            'top_h': top_log_height, 
            'width': Scale.min_dim(0.18), 
            'scored': False,
            
            'anim_type': anim_type,
            'anim_dir': anim_dir,
            'anim_speed': anim_speed,
            'center_y': bottom_log_height + (gap / 2),
            'current_gap': gap
        })

    def on_touch_down(self, touch):
        if self.back_btn.collide_point(*touch.pos): 
            return super().on_touch_down(touch) 
            
        if self.game_running: 
            self.velocity = self.jump_strength 
            return True 
        return super().on_touch_down(touch) 

    def update_physics(self, dt):
        mode = self.difficulties[self.current_diff_idx]
        log_scroll_speed = Scale.vel_w(5.0) * (dt * 60.0)

        for star in self.stars: 
            star['x'] -= self.star_scroll_speed * (dt * 60.0) 
            if star['x'] < -star['size']: 
                star['x'] = Window.width + star['size'] 
                star['y'] = random.uniform(0, Window.height) 

        if not self.game_running: 
            self.draw_game_canvas() 
            return 

        if mode == 'EASY':
            self.trail_timer += dt
            if self.trail_timer >= 0.12:
                self.trail_timer = 0.0
                self.trail_particles.append({
                    'x': self.mallow_x, 
                    'y': self.mallow_y + self.mallow_h / 4, 
                    'size': random.uniform(Scale.font(6), Scale.font(10))
                })
        
        for p in self.trail_particles:
            p['x'] -= log_scroll_speed
        self.trail_particles = [p for p in self.trail_particles if p['x'] > -p['size']]

        self.velocity += self.gravity * (dt * 60.0) 
        self.mallow_y += self.velocity * (dt * 60.0) 
        
        if self.mallow_y <= 0 or (self.mallow_y + self.mallow_h) >= Window.height:
            trigger_haptic_feedback(0.08) 
            self.game_over() 
            return 
            
        for log in self.obstacles[:]: 
            log['x'] -= log_scroll_speed
            
            if mode == 'HARD':
                if log['anim_type'] == 'SHIFT':
                    shift_delta = log['anim_dir'] * log['anim_speed'] * (dt * 60.0)
                    log['bottom_h'] += shift_delta
                    log['top_y'] += shift_delta
                    
                    if log['bottom_h'] < Scale.height_pct(0.1): log['anim_dir'] = 1
                    elif log['top_y'] > Scale.height_pct(0.9): log['anim_dir'] = -1
                    
                    log['top_h'] = Window.height - log['top_y']
                    
                elif log['anim_type'] == 'PULSE':
                    log['current_gap'] += log['anim_dir'] * log['anim_speed'] * (dt * 60.0)
                    
                    if log['current_gap'] <= Scale.height_pct(0.23): 
                        log['current_gap'] = Scale.height_pct(0.23)
                        log['anim_dir'] = 1  
                    elif log['current_gap'] >= Scale.height_pct(0.45): 
                        log['current_gap'] = Scale.height_pct(0.45)
                        log['anim_dir'] = -1 
                    
                    log['bottom_h'] = log['center_y'] - (log['current_gap'] / 2)
                    log['top_y'] = log['center_y'] + (log['current_gap'] / 2)
                    log['top_h'] = Window.height - log['top_y']
            
            if self.check_vector_collision(log):
                trigger_haptic_feedback(0.08) 
                self.game_over() 
                return 
                
            if not log['scored'] and (log['x'] + log['width']) < self.mallow_x: 
                self.score += 1 
                if self.score > self.high_score:
                    self.high_score = self.score
                self.score_label.text = f"SCORE: {self.score}  |  BEST: {self.high_score}"
                log['scored'] = True 
                
            if log['x'] < -log['width']: 
                self.obstacles.remove(log) 
                
        self.draw_game_canvas() 

    def check_vector_collision(self, log):
        mallow_radius = (self.mallow_w / 2) * 0.65 
        mallow_cx = self.mallow_x + self.mallow_w / 2 
        mallow_cy = self.mallow_y + self.mallow_h / 2 
        
        closest_x_b = max(log['x'], min(mallow_cx, log['x'] + log['width'])) 
        closest_y_b = max(0, min(mallow_cy, log['bottom_h'])) 
        dist_sq_b = (mallow_cx - closest_x_b)**2 + (mallow_cy - closest_y_b)**2 
        if dist_sq_b < (mallow_radius**2): 
            return True 
            
        closest_x_t = max(log['x'], min(mallow_cx, log['x'] + log['width'])) 
        closest_y_t = max(log['top_y'], min(mallow_cy, Window.height)) 
        dist_sq_t = (mallow_cx - closest_x_t)**2 + (mallow_cy - closest_y_t)**2 
        if dist_sq_t < (mallow_radius**2): 
            return True 
            
        return False 

    def draw_game_canvas(self):
        self.canvas.before.remove_group('toasty_vector_shapes')
        mode = self.difficulties[self.current_diff_idx]
        
        with self.canvas.before:
            star_scale = 5.0 if mode == 'NIGHTMARE' else 1.0
            for star in self.stars: 
                Color(1, 1, 1, star['opacity'], group='toasty_vector_shapes') 
                sz = star['size'] * star_scale
                Ellipse(pos=(star['x'], star['y']), size=(sz, sz), group='toasty_vector_shapes') 
                
            if mode == 'NIGHTMARE':
                Color(0.04, 0.06, 0.17, 1, group='toasty_vector_shapes') 
            elif mode == 'HARD':
                Color(0.7, 0.1, 0.1, 1, group='toasty_vector_shapes') 
            elif mode == 'DREAMY':
                Color(0.0, 0.6, 0.5, 0.8, group='toasty_vector_shapes') 
            else:
                Color(0.55, 0.27, 0.07, 1, group='toasty_vector_shapes') 
                
            for log in self.obstacles:
                Rectangle(pos=(log['x'], 0), size=(log['width'], log['bottom_h']), group='toasty_vector_shapes') 
                Rectangle(pos=(log['x'], log['top_y']), size=(log['width'], log['top_h']), group='toasty_vector_shapes') 
                
            if self.game_running and mode == 'EASY':
                Color(1, 0.71, 0.76, 0.7, group='toasty_vector_shapes')
                for p in self.trail_particles:
                    Ellipse(pos=(p['x'], p['y']), size=(p['size'], p['size']), group='toasty_vector_shapes')

            if self.game_running or self.play_help_row.opacity == 0:
                Color(1, 0.71, 0.76, 1, group='toasty_vector_shapes') 
                Rectangle(pos=(self.mallow_x, self.mallow_y), size=(self.mallow_w, self.mallow_h), group='toasty_vector_shapes') 

    def game_over(self):
        record_jbrcade_game_score("toasty_mallow", self.score)
        self.game_running = False 
        self.cleanup_engine()
        
        # Ensure fresh high score is loaded before comparing
        self.load_high_score()
        
        self.check_achievements() 
        
        is_new_high = self.score > self.high_score
        if is_new_high:
            self.high_score = self.score
            self.save_high_score()
            self.high_score_alert.opacity = 1 
        else:
            self.high_score_alert.opacity = 0 

        self.title_label.text = "TOASTED!" 
        self.title_label.opacity = 1 
        
        # Correctly format score & persistent high score label
        self.score_label.text = f"SCORE: {self.score}  |  BEST: {self.high_score}"
        self.score_label.opacity = 1
        
        self.play_help_row.opacity = 1
        self.play_help_row.disabled = False
        self.diff_row.opacity = 1
        self.diff_row.disabled = False
        self.start_btn.text = "PLAY AGAIN"
        
        # Sync color labels without overwriting self.score_label
        mode = self.difficulties[self.current_diff_idx]
        self.diff_label.text = mode
        if mode == 'DREAMY': self.diff_label.color = (0, 1, 0.8, 1)
        elif mode == 'EASY': self.diff_label.color = (0.2, 0.8, 0.2, 1)
        elif mode == 'NORMAL': self.diff_label.color = (1, 1, 1, 1)
        elif mode == 'HARD': self.diff_label.color = (1, 0.5, 0, 1)
        elif mode == 'NIGHTMARE': self.diff_label.color = (0.9, 0.1, 0.1, 1)

    def cleanup_engine(self):
        self.velocity = 0 
        if self.start_countdown_event:
            Clock.unschedule(self.start_countdown_event)
            self.start_countdown_event = None
        if self.update_event: 
            Clock.unschedule(self.update_event) 
            self.update_event = None 
        if self.spawn_event: 
            Clock.unschedule(self.spawn_event) 
            self.spawn_event = None 
            
        self.canvas.before.remove_group('toasty_vector_shapes')
        self.obstacles = []
        self.trail_particles = []

class FocusFlashScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.round_number = 1
        self.tiles_count = 3
        self.high_score = 1          
        self.generated_numbers = []
        self.target_order = []
        self.current_click_index = 0
        self.active_tiles = []
        self.decoy_tiles = []
        
        self.difficulties = ['EASY', 'NORMAL', 'HARD']
        self.current_diff_idx = 1  # Default to NORMAL
        
        # 1. Background Layer (#0A0F2C)
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        
        # Game UI Wrapper
        self.layout = RelativeLayout()
        self.add_widget(self.layout)
        
        # Status Label
        self.status_label = Label(
            text="TAP START",
            font_size=Scale.font(30),
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.90}
        )
        self.layout.add_widget(self.status_label)
        
        # HUD Tracker
        self.load_high_score()
        self.score_label = Label(
            text=f"ROUND: {self.round_number}  |  BEST: {self.high_score}",
            font_size=Scale.font(15),
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.82}
        )
        self.layout.add_widget(self.score_label)
        
        # Back Button
        self.back_btn = Button(
            text="< MENU",
            font_size=Scale.font(15),
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05),
            pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='',
            background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)
        
        # Action Row (PLAY & HELP)
        self.play_help_row = BoxLayout(
            orientation='horizontal', 
            spacing=dp(10),
            size_hint=(0.9, 0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.75, 1, 1), color=(0.04, 0.06, 0.17, 1),
            size_hint_x=0.8
        )
        self.start_btn.bind(on_release=self.start_countdown_sequence)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size=Scale.font(16), font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

        # Difficulty Scroll Wheel Row (Positioned at y=0.1)
        self.diff_row = BoxLayout(
            orientation='horizontal', spacing=dp(10), 
            size_hint=(0.9, None), height=dp(45),
            pos_hint={'center_x': 0.5, 'center_y': 0.1}
        )
        self.layout.add_widget(self.diff_row)

        self.prev_diff_btn = Button(
            text="<", font_name='assets/fonts/ARCADE_N.TTF', font_size=Scale.font(16), size_hint_x=0.2,
            background_normal='', background_color=(0, 0.75, 1, 0.3), color=(0, 0.75, 1, 1)
        )
        self.prev_diff_btn.bind(on_release=lambda x: self.cycle_difficulty(-1))
        self.diff_row.add_widget(self.prev_diff_btn)

        self.diff_label = Label(
            text="NORMAL", font_name='assets/fonts/ARCADE_N.TTF', font_size=Scale.font(16),
            color=(1, 1, 1, 1), halign='center'
        )
        self.diff_row.add_widget(self.diff_label)

        self.next_diff_btn = Button(
            text=">", font_name='assets/fonts/ARCADE_N.TTF', font_size=Scale.font(16), size_hint_x=0.2,
            background_normal='', background_color=(0, 0.75, 1, 0.3), color=(0, 0.75, 1, 1)
        )
        self.next_diff_btn.bind(on_release=lambda x: self.cycle_difficulty(1))
        self.diff_row.add_widget(self.next_diff_btn)

    def cycle_difficulty(self, direction):
        if hasattr(self, 'game_running') and self.game_running: return
        self.current_diff_idx = (self.current_diff_idx + direction) % len(self.difficulties)
        self.update_difficulty_ui()

    def update_difficulty_ui(self):
        mode = self.difficulties[self.current_diff_idx]
        self.diff_label.text = mode
        self.load_high_score()
        
        if mode == 'EASY': self.diff_label.color = (0.2, 0.8, 0.2, 1)
        elif mode == 'NORMAL': self.diff_label.color = (1, 1, 1, 1)
        elif mode == 'HARD': self.diff_label.color = (0.9, 0.1, 0.1, 1)
        
        self.score_label.text = f"ROUND: {self.round_number}  |  BEST: {self.high_score}"

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.diff_row.disabled = True
        self.back_btn.disabled = True
        
        game_name = "Focus Flash"
        placeholders = [
            "Numbered cards will flash briefly on your screen",
            "Rely on your peripheral vision to capture their positions and values",
            "Tap the blank cards in ascending numerical order"
        ]
        
        overlay = InstructionOverlay(
            game_name=game_name, 
            rules_list=placeholders, 
            close_callback=self.on_instructions_closed
        )
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.diff_row.disabled = False
        self.back_btn.disabled = False
    
    def on_pre_enter(self, *args):
        self.update_difficulty_ui()
        self.reset_screen_to_baseline()

    def on_leave(self, *args):
        Clock.unschedule(self.handle_countdown_tick)
        self.clear_previous_tiles()

    def reset_screen_to_baseline(self):
        self.clear_previous_tiles()
        self.round_number = 1
        
        self.status_label.font_size = Scale.font(30)
        self.status_label.text = "TAP START"
        self.score_label.text = f"ROUND: {self.round_number}  |  BEST: {self.high_score}"
        
        self.play_help_row.opacity = 1
        self.play_help_row.disabled = False
        self.diff_row.opacity = 1
        self.diff_row.disabled = False
        
        self.start_btn.text = "START GAME"
        self.start_btn.background_color = (0, 0.75, 1, 1)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def go_back_to_menu(self, instance):
        self.manager.current = 'menu'

    def load_high_score(self):
        mode = self.difficulties[self.current_diff_idx].lower()
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get(f'focus_flash_{mode}_high', 1)
        except Exception:
            self.high_score = 1

    def save_high_score(self):
        mode = self.difficulties[self.current_diff_idx].lower()
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data[f'focus_flash_{mode}_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def start_countdown_sequence(self, instance):
        self.play_help_row.opacity = 0
        self.play_help_row.disabled = True
        self.diff_row.opacity = 0
        self.diff_row.disabled = True
        
        self.clear_previous_tiles()
        
        mode = self.difficulties[self.current_diff_idx]
        if mode == 'EASY':
            self.tiles_count = 2 + ((self.round_number - 1) // 5)
        elif mode == 'NORMAL':
            self.tiles_count = 3 + ((self.round_number - 1) // 5)
        else: # HARD
            self.tiles_count = 4 + ((self.round_number - 1) // 5)
            
        self.status_label.font_size = Scale.font(30)
        self.score_label.text = f"ROUND: {self.round_number}  |  BEST: {self.high_score}"
        
        self.generate_sequence_by_difficulty()
        
        self.countdown_ticks = 3
        self.status_label.text = str(self.countdown_ticks)
        Clock.unschedule(self.handle_countdown_tick) 
        Clock.schedule_interval(self.handle_countdown_tick, 1.0)

    def handle_countdown_tick(self, dt):
        self.countdown_ticks -= 1
        if self.countdown_ticks > 0:
            self.status_label.text = str(self.countdown_ticks)
        else:
            self.status_label.font_size = Scale.font(30)
            self.status_label.text = "FOCUS!"
            Clock.unschedule(self.handle_countdown_tick)
            self.spawn_flash_tiles()

    def generate_sequence_by_difficulty(self):
        mode = self.difficulties[self.current_diff_idx]
        start_num = random.randint(1, 20)

        if mode == 'EASY':
            # Sequential runs (1-2-3, 5-6-7, etc.)
            self.generated_numbers = [start_num + i for i in range(self.tiles_count)]
        elif mode == 'NORMAL':
            # Multiples & fixed steps (+2, +5, +10, etc.)
            step = random.choice([2, 3, 5, 10])
            self.generated_numbers = [start_num + (i * step) for i in range(self.tiles_count)]
        else: # HARD
            # Large steps & non-linear random jumps
            self.generated_numbers = sorted(random.sample(range(10, 99), self.tiles_count))
        
        self.target_order = list(self.generated_numbers)
        self.current_click_index = 0

    def spawn_flash_tiles(self):
        mode = self.difficulties[self.current_diff_idx]
        tile_size = Scale.min_dim(0.15)
        
        # Grid bounds per difficulty tier
        if mode == 'EASY':
            min_x, max_x = Window.width * 0.30, Window.width * 0.55
            min_y, max_y = Window.height * 0.35, Window.height * 0.50
        else:
            min_x, max_x = Window.width * 0.12, Window.width * 0.72
            min_y, max_y = Window.height * 0.28, Window.height * 0.65

        # --- 5% Soft-Overlap Collision Logic ---
        min_allowed_distance = tile_size * 0.95

        placed_positions = []
        all_targets = list(self.generated_numbers)
        
        # Add 1 decoy blank card for Hard mode
        num_decoys = 1 if mode == 'HARD' else 0

        for num in all_targets:
            pos_x, pos_y = self.find_valid_spawn_pos(min_x, max_x, min_y, max_y, min_allowed_distance, placed_positions)
            placed_positions.append((pos_x, pos_y))

            btn = Button(
                text=str(num),
                font_size=Scale.font(20),  
                font_name='assets/fonts/ARCADE_N.TTF',
                color=(0, 0.75, 1, 1), 
                size_hint=(None, None),
                size=(tile_size, tile_size),
                pos=(pos_x, pos_y),
                background_normal='',
                background_color=(0.12, 0.16, 0.32, 1) 
            )
            btn.target_value = num
            btn.bind(on_release=self.handle_tile_selection)
            
            self.layout.add_widget(btn)
            self.active_tiles.append(btn)

        # Spawn Decoy Cards
        for _ in range(num_decoys):
            pos_x, pos_y = self.find_valid_spawn_pos(min_x, max_x, min_y, max_y, min_allowed_distance, placed_positions)
            placed_positions.append((pos_x, pos_y))

            decoy = Button(
                text="",
                size_hint=(None, None),
                size=(tile_size, tile_size),
                pos=(pos_x, pos_y),
                background_normal='',
                background_color=(0.12, 0.16, 0.32, 0.6)
            )
            self.layout.add_widget(decoy)
            self.decoy_tiles.append(decoy)

        # Dynamic Flash Duration Scaling
        if mode == 'EASY':
            flash_time = max(1.5, 2.0 - (self.round_number - 1) * 0.05)
        elif mode == 'NORMAL':
            flash_time = max(0.8, 1.2 - (self.round_number - 1) * 0.04)
        else: # HARD
            flash_time = max(0.5, 0.8 - (self.round_number - 1) * 0.03)

        Clock.schedule_once(self.hide_tile_values, flash_time)

    def find_valid_spawn_pos(self, min_x, max_x, min_y, max_y, min_dist, placed_positions):
        for _ in range(150):
            test_x = random.uniform(min_x, max_x)
            test_y = random.uniform(min_y, max_y)
            
            overlap = False
            for px, py in placed_positions:
                if abs(px - test_x) < min_dist and abs(py - test_y) < min_dist:
                    overlap = True
                    break
            if not overlap:
                return test_x, test_y
                
        return random.uniform(min_x, max_x), random.uniform(min_y, max_y)

    def hide_tile_values(self, dt):
        # Remove Decoy Cards completely when flash ends
        for decoy in self.decoy_tiles:
            if decoy.parent:
                decoy.parent.remove_widget(decoy)
        self.decoy_tiles = []

        if not self.active_tiles: return
        self.status_label.font_size = Scale.font(16)
        self.status_label.text = "TAP TILES IN ORDER!"
        for tile in self.active_tiles:
            tile.text = "" 
            tile.background_color = (0.18, 0.26, 0.48, 1)

    def handle_tile_selection(self, instance):
        if self.status_label.text == "FOCUS!": return
        
        expected_value = self.target_order[self.current_click_index]
        
        if instance.target_value == expected_value:
            instance.text = str(instance.target_value)
            instance.font_size = Scale.font(20)
            instance.color = (1, 1, 1, 1)
            instance.background_color = (0.1, 0.6, 0.3, 1)
            instance.disabled = True
            self.current_click_index += 1
            
            if self.current_click_index == len(self.target_order):
                self.status_label.font_size = Scale.font(20)
                self.status_label.text = "ROUND COMPLETE!"
                self.round_number += 1
                Clock.schedule_once(lambda dt: self.show_next_round_button(), 1.0)
        else:
            trigger_haptic_feedback(0.08)
            instance.background_color = (0.75, 0.15, 0.15, 1)
            
            if self.round_number > self.high_score:
                self.high_score = self.round_number
                self.save_high_score()
                self.status_label.font_size = Scale.font(15)
                self.status_label.text = f"NEW HIGH SCORE!\nREACHED ROUND {self.round_number}"
            else:
                self.status_label.font_size = Scale.font(15)
                self.status_label.text = f"GAME OVER!\nFAILED ON {instance.target_value}"
                
            self.round_number = 1 
            Clock.schedule_once(lambda dt: self.show_next_round_button(reset=True), 0.5)

    def show_next_round_button(self, reset=False):
        if self.manager and self.manager.current != self.name: return
        
        self.clear_previous_tiles()
        if reset:
            self.start_btn.text = "RETRY"
            self.start_btn.background_color = (0.75, 0.2, 0.2, 1)
        else:
            self.start_btn.text = f"START ROUND {self.round_number}"
            self.start_btn.background_color = (0, 0.75, 1, 1)
            
        self.score_label.text = f"ROUND: {self.round_number}  |  BEST: {self.high_score}"
        
        self.play_help_row.opacity = 1
        self.play_help_row.disabled = False
        self.diff_row.opacity = 1
        self.diff_row.disabled = False

    def clear_previous_tiles(self):
        for tile in self.active_tiles:
            if tile.parent:
                tile.parent.remove_widget(tile)
        for decoy in self.decoy_tiles:
            if decoy.parent:
                decoy.parent.remove_widget(decoy)
        self.active_tiles = []
        self.decoy_tiles = []
        
class PlanetHopperScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.round_number = 1
        self.high_score = 1          
        self.planets = []   
        self.hopper_path = []  
        self.player_path = []  
        self.current_step = 0  
        self.game_state = "IDLE"  
        self.wrong_planet_idx = None 
        
        self.difficulties = ['EASY', 'NORMAL', 'HARD']
        self.current_diff_idx = 1  # Default to NORMAL
        
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)  
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        
        self.score_label = Label(
            text="ROUND: 1| BEST: 1|",
            font_size='12sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.36, 'center_y': 0.8}
        )
        self.layout.add_widget(self.score_label)
        
        self.hops_label = Label(
            text="HOPS: 3", 
            font_size='12sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.8, 'center_y': 0.8}
        )
        self.layout.add_widget(self.hops_label)
        
        self.status_label = Label(
            text="TAP START",
            font_size=Scale.font(30),
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.9}
        )
        self.layout.add_widget(self.status_label)
        
        self.back_btn = Button(
            text="< MENU",
            font_size=Scale.font(15),
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05),
            pos_hint={'x': 0.0, 'top': 1},
            background_normal='',
            background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)
        
        # 🟢 STANDARDIZED ROW WRAPPER AT y=0.2 (Matching All Other Mini-Games)
        self.play_help_row = BoxLayout(
            orientation='horizontal', spacing=dp(10),
            size_hint=(0.9, 0.1), pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.75, 1, 1), color=(0.04, 0.06, 0.17, 1),
            size_hint_x=0.8
        )
        self.start_btn.bind(on_release=self.start_game)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size='16sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

        # Difficulty Selector Component Row (Positioned at y=0.1)
        self.diff_row = BoxLayout(
            orientation='horizontal', spacing=dp(10), 
            size_hint=(0.9, None), height=dp(45),
            pos_hint={'center_x': 0.5, 'center_y': 0.1}
        )
        self.layout.add_widget(self.diff_row)

        self.prev_diff_btn = Button(
            text="<", font_name='assets/fonts/ARCADE_N.TTF', font_size='16sp', size_hint_x=0.2,
            background_normal='', background_color=(0, 0.75, 1, 0.3), color=(0, 0.75, 1, 1)
        )
        self.prev_diff_btn.bind(on_release=lambda x: self.cycle_difficulty(-1))
        self.diff_row.add_widget(self.prev_diff_btn)

        self.diff_label = Label(
            text="NORMAL", font_name='assets/fonts/ARCADE_N.TTF', font_size=Scale.font(16),
            color=(1, 1, 1, 1), halign='center'
        )
        self.diff_row.add_widget(self.diff_label)

        self.next_diff_btn = Button(
            text=">", font_name='assets/fonts/ARCADE_N.TTF', font_size='16sp', size_hint_x=0.2,
            background_normal='', background_color=(0, 0.75, 1, 0.3), color=(0, 0.75, 1, 1)
        )
        self.next_diff_btn.bind(on_release=lambda x: self.cycle_difficulty(1))
        self.diff_row.add_widget(self.next_diff_btn)

        self.generate_universe()
        self.load_high_score()

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.diff_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Planet Hopper"
        placeholders = [
            "Keep track of which planets the red dot hops to",
            "Tap on those planets in the same order",
            "The red dot will make more hops as the rounds progress"
        ]
        overlay = InstructionOverlay(game_name=game_name, rules_list=placeholders, close_callback=self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.diff_row.disabled = False
        self.back_btn.disabled = False

    def on_pre_enter(self, *args):
        self.game_state = "IDLE"
        self.round_number = 1
        self.wrong_planet_idx = None
        self.play_help_row.opacity = 1
        self.play_help_row.disabled = False
        self.diff_row.opacity = 1
        self.diff_row.disabled = False
        self.start_btn.text = "START GAME"
        self.start_btn.background_color = (0, 0.75, 1, 1)
        self.status_label.text = "TAP START"
        self.clear_previous_tiles()
        self.update_difficulty_ui()

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.draw_game_elements()

    def cycle_difficulty(self, direction):
        if self.game_state not in ["IDLE", "GAME_OVER"]: return
        self.current_diff_idx = (self.current_diff_idx + direction) % len(self.difficulties)
        self.update_difficulty_ui()

    def update_difficulty_ui(self):
        mode = self.difficulties[self.current_diff_idx]
        self.diff_label.text = mode
        self.load_high_score()
        
        if mode == 'EASY': self.diff_label.color = (0.2, 0.8, 0.2, 1)
        elif mode == 'NORMAL': self.diff_label.color = (1, 1, 1, 1)
        elif mode == 'HARD': self.diff_label.color = (0.9, 0.1, 0.1, 1)
        
        if self.game_state == "GAME_OVER":
            self.round_number = 1
        self.score_label.text = f"ROUND: {self.round_number}| BEST: {self.high_score}|"

    def go_back_to_menu(self, instance):
        Animation.cancel_all(self) 
        self.game_state = "IDLE"
        self.clear_previous_tiles()
        self.manager.current = 'menu'

    def load_high_score(self):
        mode = self.difficulties[self.current_diff_idx]
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get(f'planet_hopper_{mode.lower()}_high', 1)
        except Exception:
            self.high_score = 1

    def save_high_score(self):
        mode = self.difficulties[self.current_diff_idx]
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data[f'planet_hopper_{mode.lower()}_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def generate_universe(self):
        self.planets = []
        center_x, center_y = Window.width / 2, Window.height / 2
        deadzone_radius = Window.width * 0.22
        
        colors = [
            (0, 0.6, 0.9, 1),    # Electric Blue
            (0.6, 0.2, 0.8, 1),  # Nebula Purple
            (0.9, 0.7, 0, 1),    # Cosmic Gold
            (0.1, 0.8, 0.9, 1),  # Cyan
            (0.8, 0.4, 0, 1)     # Orange Dust
        ]
        
        planet_idx = 0
        while len(self.planets) < 20:
            x = random.uniform(Window.width * 0.1, Window.width * 0.9)
            y = random.uniform(Window.height * 0.12, Window.height * 0.76)
            radius = random.uniform(Window.width * 0.04, Window.width * 0.06)
            
            dist_to_center = ((x - center_x)**2 + (y - center_y)**2)**0.5
            if dist_to_center < deadzone_radius:
                continue
                
            overlap = False
            for p in self.planets:
                dist_nodes = ((x - p['pos'][0])**2 + (y - p['pos'][1])**2)**0.5
                if dist_nodes < (radius + p['radius'] + 15):
                    overlap = True
                    break
            
            if not overlap:
                self.planets.append({
                    'pos': [x, y],
                    'radius': radius,
                    'base_radius': radius, 
                    'color': random.choice(colors),
                    'id': planet_idx
                })
                planet_idx += 1

        self.center_pos = [center_x, center_y]
        self.hopper_pos = list(self.center_pos)
        self.player_pos = None

    def start_game(self, instance):
        self.play_help_row.opacity = 0
        self.play_help_row.disabled = True
        self.diff_row.opacity = 0
        self.diff_row.disabled = True
        self.round_number = 1
        self.wrong_planet_idx = None
        self.generate_universe()
        self.start_round()

    def start_round(self):
        self.player_path = []
        self.wrong_planet_idx = None
        mode = self.difficulties[self.current_diff_idx]
        
        if mode == 'EASY':
            self.base_hops = 2 + ((self.round_number - 1) // 7) 
        elif mode == 'HARD':
            self.base_hops = 4 + ((self.round_number - 1) // 5) 
        else:
            self.base_hops = 3 + ((self.round_number - 1) // 5) 
        
        if self.round_number == 1:
            total_hops_needed = self.base_hops + 0
        else:
            total_hops_needed = self.base_hops

        self.score_label.text = f"ROUND: {self.round_number}| BEST: {self.high_score}|"
        self.hops_label.text = f"HOPS: {total_hops_needed}"
        self.status_label.text = "WATCH THE HOPPER!"
        
        available_indices = list(range(len(self.planets)))
        
        if self.round_number == 1:
            self.hopper_path = random.sample(available_indices, total_hops_needed)
            self.player_pos = list(self.center_pos)
        else:
            last_hopper_planet_idx = self.hopper_path[-1]
            if last_hopper_planet_idx in available_indices:
                available_indices.remove(last_hopper_planet_idx)
            new_hops = random.sample(available_indices, total_hops_needed - 1)
            self.hopper_path = [last_hopper_planet_idx] + new_hops

        self.game_state = "HOPPER_TURN"
        self.current_step = 0
        Clock.schedule_once(self.animate_hopper_step, 1.0)

    def animate_hopper_step(self, dt):
        if self.game_state != "HOPPER_TURN": return
        
        if self.current_step < len(self.hopper_path):
            target_planet = self.planets[self.hopper_path[self.current_step]]
            mode = self.difficulties[self.current_diff_idx]
            
            anim_duration = 0.8 if mode == 'EASY' else 0.5
            step_delay = 0.5 if mode == 'EASY' else 0.3
            
            if mode == 'EASY':
                target_planet['radius'] = target_planet['base_radius'] * 1.35
            
            anim = Animation(hopper_pos=target_planet['pos'], duration=anim_duration, t='out_quad')
            anim.bind(on_progress=lambda a, w, p: self.draw_game_elements())
            anim.bind(on_complete=lambda a, w: self.on_hopper_step_done(step_delay, target_planet))
            anim.start(self)
        else:
            self.game_state = "PLAYER_TURN"
            self.status_label.text = "YOUR TURN!\nFOLLOW THE PATH"
            self.draw_game_elements()

    def on_hopper_step_done(self, delay, active_planet):
        active_planet['radius'] = active_planet['base_radius']
        self.current_step += 1
        Clock.schedule_once(self.animate_hopper_step, delay)

    def on_touch_down(self, touch):
        if self.back_btn.collide_point(*touch.pos):
            return super().on_touch_down(touch)
            
        if self.game_state != "PLAYER_TURN":
            return super().on_touch_down(touch)
            
        for idx, p in enumerate(self.planets):
            distance = ((touch.x - p['pos'][0])**2 + (touch.y - p['pos'][1])**2)**0.5
            if distance <= p['radius'] * 1.6:
                self.handle_player_move(idx)
                return True
        return super().on_touch_down(touch)

    def handle_player_move(self, planet_idx):
        expected_idx = self.hopper_path[len(self.player_path)]
        
        if planet_idx == expected_idx:
            target_planet = self.planets[planet_idx]
            anim = Animation(player_pos=target_planet['pos'], duration=0.4, t='out_quad')
            anim.bind(on_progress=lambda a, w, p: self.draw_game_elements())
            
            self.player_path.append(planet_idx)
            total_clicks_needed = len(self.hopper_path) - 1
            
            if len(self.player_path) == total_clicks_needed:
                self.game_state = "IDLE"
                anim.bind(on_complete=lambda a, w: self.trigger_win_transition())
                
            anim.start(self)
        else:
            self.wrong_planet_idx = planet_idx
            self.game_state = "GAME_OVER"
            trigger_haptic_feedback(0.08)
            
            if self.round_number > self.high_score:
                self.high_score = self.round_number
                self.save_high_score()
                self.status_label.text = f"NEW BEST!\nREACHED ROUND {self.round_number}"
            else:
                self.status_label.text = "WRONG ORDER! GAME OVER"
                
            self.clear_previous_tiles()
            
            self.play_help_row.opacity = 1
            self.play_help_row.disabled = False
            self.diff_row.opacity = 1
            self.diff_row.disabled = False
            self.start_btn.text = "RETRY"
            self.start_btn.background_color = (0.75, 0.2, 0.2, 1)
            
            self.update_difficulty_ui()

    def trigger_win_transition(self):
        self.status_label.text = "PERFECT!"
        self.round_number += 1
        Clock.schedule_once(lambda dt: self.start_round(), 1.0)

    def draw_game_elements(self):
        self.canvas.remove_group('game_shapes')
        if not self.planets or self.game_state == "GAME_OVER": return
        
        mode = self.difficulties[self.current_diff_idx]
        
        with self.canvas:
            for idx, p in enumerate(self.planets):
                if mode == 'HARD':
                    Color(0.35, 0.40, 0.48, 1, group='game_shapes')
                else:
                    Color(*p['color'], group='game_shapes')
                
                Ellipse(
                    pos=(p['pos'][0] - p['radius'], p['pos'][1] - p['radius']),
                    size=(p['radius'] * 2, p['radius'] * 2),
                    group='game_shapes'
                )
            
            if self.hopper_pos:
                Color(1, 0.1, 0.2, 1, group='game_shapes')
                r = Window.width * 0.025
                Ellipse(pos=(self.hopper_pos[0] - r, self.hopper_pos[1] - r), size=(r * 2, r * 2), group='game_shapes')
                
            if self.player_pos:
                Color(0.1, 0.9, 0.2, 1, group='game_shapes')
                r = Window.width * 0.025
                Ellipse(pos=(self.player_pos[0] - r, self.player_pos[1] - r), size=(r * 2, r * 2), group='game_shapes')

    def clear_previous_tiles(self):
        self.planets = []
        self.hopper_pos = None
        self.player_pos = None
        self.canvas.remove_group('game_shapes')
        
class StroopMatchScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.score = 0
        self.high_score = 0          
        self.time_remaining = 60
        self.game_active = False
        self.timer_event = None
        
        self.colors_map = {
            'RED': (0.9, 0.2, 0.2, 1), 'BLUE': (0.2, 0.5, 0.9, 1),
            'GREEN': (0.1, 0.7, 0.3, 1), 'YELLOW': (0.9, 0.8, 0.1, 1), 'BLACK': (0.05, 0.05, 0.05, 1)
        }
        self.color_names = list(self.colors_map.keys())

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.title_label = Label(
            text="DO THEY MATCH?", font_size=Scale.font(30), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.90}
        )
        self.layout.add_widget(self.title_label)

        self.timer_label = Label(
            text="TIME: 60s", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.82}
        )
        self.layout.add_widget(self.timer_label)

        self.load_high_score()
        self.hi_score_label = Label(
            text=f"BEST: {self.high_score}", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.75}
        )
        self.layout.add_widget(self.hi_score_label)

        self.card_container = RelativeLayout(size_hint=(1, 1))
        self.layout.add_widget(self.card_container)

        self.top_card = Label(
            text="COLOR", font_size='20sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0, 0, 1), size_hint=(0.55, 0.12), pos_hint={'x': 0.08, 'center_y': 0.60}
        )
        with self.top_card.canvas.before:
            Color(1, 1, 1, 1)
            self.top_bg = Rectangle(pos=self.top_card.pos, size=self.top_card.size)
        self.top_card.bind(pos=self.sync_card_geometry, size=self.sync_card_geometry)

        self.bottom_card = Label(
            text="INK", font_size='20sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 0, 0, 1), size_hint=(0.55, 0.12), pos_hint={'x': 0.08, 'center_y': 0.44}
        )
        with self.bottom_card.canvas.before:
            Color(1, 1, 1, 1)
            self.bottom_bg = Rectangle(pos=self.bottom_card.pos, size=self.bottom_card.size)
        self.bottom_card.bind(pos=self.sync_card_geometry, size=self.sync_card_geometry)

        self.yes_btn = Button(
            text="Y", font_size='24sp', font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.18, 0.12), pos_hint={'x': 0.72, 'center_y': 0.60},
            background_normal='', background_color=(0, 0.6, 0.3, 1)
        )
        self.yes_btn.bind(on_release=lambda x: self.process_user_answer(True))

        self.no_btn = Button(
            text="N", font_size='24sp', font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.18, 0.12), pos_hint={'x': 0.72, 'center_y': 0.44},
            background_normal='', background_color=(0.75, 0.15, 0.15, 1)
        )
        self.no_btn.bind(on_release=lambda x: self.process_user_answer(False))

        # 🟢 ROW WRAPPER
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10), 
            size_hint=(0.9,0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), size_hint_x=0.8,
            background_normal='', background_color=(0, 0.75, 1, 1)
        )
        self.start_btn.bind(on_release=self.start_stroop_game)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size='16sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Stroop Match"
        placeholders = [
            "Compare the top card color name to the bottom card font color",
            "Do not read the text on the bottom card; this is meant to throw you off",
            "Press Y if they match or N if they do not match"
        ]
        overlay = InstructionOverlay(game_name=game_name, rules_list=placeholders, close_callback=self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def on_leave(self):
        self.stop_game_engine()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def sync_card_geometry(self, instance, value):
        if instance == self.top_card:
            self.top_bg.pos = instance.pos
            self.top_bg.size = instance.size
        elif instance == self.bottom_card:
            self.bottom_bg.pos = instance.pos
            self.bottom_bg.size = instance.size

    def go_back_to_menu(self, instance):
        self.stop_game_engine()
        self.manager.current = 'menu'

    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('stroop_match_high', 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['stroop_match_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def start_stroop_game(self, instance):
        self.score = 0
        self.time_remaining = 60
        self.game_active = True
        
        self.layout.remove_widget(self.play_help_row)
        
        if self.card_container not in self.layout.children:
            self.layout.add_widget(self.card_container)
        if self.top_card not in self.card_container.children:
            self.card_container.add_widget(self.top_card)
        if self.bottom_card not in self.card_container.children:
            self.card_container.add_widget(self.bottom_card)
        if self.yes_btn not in self.layout.children:
            self.layout.add_widget(self.yes_btn)
        if self.no_btn not in self.layout.children:
            self.layout.add_widget(self.no_btn)
            
        self.timer_label.text = f"TIME: {self.time_remaining}s"
        self.hi_score_label.text = f"BEST: {self.high_score}"
        self.title_label.text = "DO THEY MATCH?"
        self.title_label.color = (0, 0.75, 1, 1)
        self.generate_next_challenge()
        
        if self.timer_event: 
            Clock.unschedule(self.timer_event)
        self.timer_event = Clock.schedule_interval(self.handle_clock_tick, 1.0)

    def generate_next_challenge(self):
        should_match = random.choice([True, False])
        if should_match:
            self.top_text_name = random.choice(self.color_names)
            self.target_ink_color_name = self.top_text_name
            self.bottom_text_name = random.choice(self.color_names)
        else:
            self.top_text_name = random.choice(self.color_names)
            remaining_colors = [c for c in self.color_names if c != self.top_text_name]
            self.target_ink_color_name = random.choice(remaining_colors)
            self.bottom_text_name = random.choice(self.color_names)
        
        self.top_card.text = self.top_text_name
        self.bottom_card.text = self.bottom_text_name
        self.bottom_card.color = self.colors_map[self.target_ink_color_name]
        self.correct_match_answer = (self.top_text_name == self.target_ink_color_name)

    def process_user_answer(self, user_pressed_yes):
        if not self.game_active: return
        if user_pressed_yes == self.correct_match_answer:
            self.score += 1
            self.generate_next_challenge()
        else:
            self.game_active = False  
            self.yes_btn.background_color = (0, 0.6, 0.3, 0.2)  
            self.no_btn.background_color = (0.75, 0.15, 0.15, 0.2)  
            self.title_label.text = "WRONG! 1s PENALTY"
            trigger_haptic_feedback(0.08)
            self.title_label.color = (0.9, 0.2, 0.2, 1)  
            Clock.schedule_once(self.lift_penalty_cooldown, 1.0)
            
    def lift_penalty_cooldown(self, dt):
        if self.time_remaining <= 0: return
        self.game_active = True  
        self.yes_btn.background_color = (0, 0.6, 0.3, 1)
        self.no_btn.background_color = (0.75, 0.15, 0.15, 1)
        self.title_label.text = "DO THEY MATCH?"
        self.title_label.color = (0, 0.75, 1, 1)  
        self.generate_next_challenge()

    def handle_clock_tick(self, dt):
        self.time_remaining -= 1
        if self.time_remaining > 0:
            self.timer_label.text = f"TIME: {self.time_remaining}s"
        else:
            self.stop_game_engine()

    def stop_game_engine(self):
        self.game_active = False
        if self.timer_event:
            Clock.unschedule(self.handle_clock_tick)
            self.timer_event = None
        Clock.unschedule(self.lift_penalty_cooldown)
            
        self.layout.remove_widget(self.card_container)
        self.layout.remove_widget(self.yes_btn)
        self.layout.remove_widget(self.no_btn)
        
        self.yes_btn.background_color = (0, 0.6, 0.3, 1)
        self.no_btn.background_color = (0.75, 0.15, 0.15, 1)
        
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
            self.title_label.text = "NEW HIGH SCORE!"
            self.title_label.color = (1, 0.84, 0, 1)
        else:
            self.title_label.text = "TIME UP!"
            self.title_label.color = (0, 0.75, 1, 1)
            
        #self.timer_label.text = f"FINAL SCORE: {self.score}"
        self.hi_score_label.text = f"BEST: {self.high_score}"
        
        if self.play_help_row not in self.layout.children:
            self.start_btn.text = "PLAY AGAIN"
            self.play_help_row.disabled = False
            self.layout.add_widget(self.play_help_row)

class AirTrafficControlScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.round_number = 1
        self.high_score = 1       
        self.plane_count = 3
        self.planes = []         
        self.target_order = []   
        self.current_click_index = 0
        self.game_state = "IDLE"  
        self.wrong_plane_id = None
        self.timer_seconds = 5
        self.clock_event = None
        
        self.layout = RelativeLayout()
        self.add_widget(self.layout)
        
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        
        self.load_high_score()
        self.score_label = Label(
            text=f"ROUND: {self.round_number}  |  BEST: {self.high_score}",
            font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF', color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.85}
        )
        self.layout.add_widget(self.score_label)
        
        self.planes_count_label = Label(
            text=f"PLANES: {self.plane_count}", font_size='12sp',
            font_name='assets/fonts/ARCADE_N.TTF', color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.8}
        )
        self.layout.add_widget(self.planes_count_label)
        
        self.status_label = Label(
            text="TAP START", font_size=Scale.font(30),
            font_name='assets/fonts/ARCADE_N.TTF', color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.90}
        )
        self.layout.add_widget(self.status_label)
        
        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)
        
        # 🟢 ROW WRAPPER
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10), 
            size_hint=(0.9,0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="start game", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), size_hint_x=0.8,
            background_normal='', background_color=(0, 0.75, 1, 1)
        )
        self.start_btn.bind(on_release=self.start_game)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size='14sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Air Traffic Control"
        placeholders = [
            "Memorize the ID numbers assigned to each plane",
            "Track their positions while the labels vanish mid-flight",
            "Tap the planes in sequential numerical order when they stop"
        ]
        overlay = InstructionOverlay(game_name=game_name, rules_list=placeholders, close_callback=self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def on_pre_enter(self):
        self.stop_game_clock()
        self.game_state = "IDLE"
        self.round_number = 1
        self.plane_count = 3
        self.status_label.text = "TAP START"
        self.clear_radar_screen()
        if self.play_help_row not in self.layout.children:
            self.layout.add_widget(self.play_help_row)
        self.start_btn.text = "START GAME"
        self.start_btn.background_color = (0, 0.75, 1, 1)
        self.play_help_row.disabled = False
        if self.back_btn not in self.layout.children:
            self.layout.add_widget(self.back_btn)
        self.score_label.text = f"ROUND: {self.round_number}  |  BEST: {self.high_score}"
        self.planes_count_label.text = f"PLANES: {self.plane_count}"

    def on_leave(self, *args):
        self.stop_game_clock()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.draw_radar_elements()

    def go_back_to_menu(self, instance):
        self.stop_game_clock()
        self.game_state = "IDLE"
        self.round_number = 1
        self.plane_count = 3
        if self.play_help_row not in self.layout.children:
            self.layout.add_widget(self.play_help_row)
        self.start_btn.text = "START GAME"
        self.start_btn.background_color = (0, 0.75, 1, 1)
        self.play_help_row.disabled = False
        self.status_label.text = "TAP START"
        self.clear_radar_screen()
        self.manager.current = 'menu'

    def stop_game_clock(self):
        if self.clock_event:
            Clock.unschedule(self.clock_event)
            self.clock_event = None

    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('air_traffic_control_high_round', 1)
        except Exception:
            self.high_score = 1

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['air_traffic_control_high_round'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def start_game(self, instance):
        self.layout.remove_widget(self.play_help_row)
        if self.back_btn not in self.layout.children:
            self.layout.add_widget(self.back_btn)
        self.round_number = 1
        self.plane_count = 3
        self.start_round()

    def start_round(self):
        self.stop_game_clock()
        self.clear_plane_labels()
        self.wrong_plane_id = None
        self.current_click_index = 0
        self.plane_count = 3 + ((self.round_number - 1) // 3)
        self.score_label.text = f"ROUND: {self.round_number}  |  BEST: {self.high_score}"
        self.planes_count_label.text = f"PLANES: {self.plane_count}"
        self.planes = []
        self.target_order = list(range(1, self.plane_count + 1))
        start_y = Window.height * 0.5
        spacing_x = Window.width / (self.plane_count + 1)
        for i in range(self.plane_count):
            plane_id = i + 1
            pos_x = spacing_x * plane_id
            initial_angle = math.radians(90 + random.uniform(-20, 20))
            self.planes.append({
                'pos': [pos_x, start_y], 'angle': initial_angle, 'target_angle': initial_angle,
                'speed': random.uniform(Window.width * 0.005, Window.width * 0.008), 'id': plane_id, 'clicked': False
            })
        self.game_state = "COUNTDOWN"
        self.timer_seconds = 5
        self.status_label.text = f"MEMORIZE IDS: {self.timer_seconds}s"
        self.render_plane_labels()
        self.draw_radar_elements()
        self.clock_event = Clock.schedule_interval(self.handle_countdown_tick, 1.0)

    def handle_countdown_tick(self, dt):
        self.timer_seconds -= 1
        if self.timer_seconds > 0:
            self.status_label.text = f"MEMORIZE IDS: {self.timer_seconds}s"
        else:
            self.stop_game_clock()
            self.clear_plane_labels()
            self.begin_flight_phase()

    def begin_flight_phase(self):
        self.game_state = "FLYING"
        self.timer_seconds = 5
        self.status_label.text = "TRACK THE PLANES!"
        self.clock_event = Clock.schedule_interval(self.update_flight_physics, 1.0 / 60.0)

    def update_flight_physics(self, dt):
        if self.game_state != "FLYING": return
        self.timer_seconds -= dt
        if self.timer_seconds <= 0:
            self.stop_game_clock()
            self.game_state = "PLAYER_TURN"
            self.status_label.text = "TAP IN ORDER\n(1, 2, 3...)"
            self.draw_radar_elements()
            return
        min_x, max_x = Window.width * 0.06, Window.width * 0.94
        min_y, max_y = Window.height * 0.14, Window.height * 0.76
        turn_speed = 0.06
        for p in self.planes:
            if random.random() < 0.02:
                p['target_angle'] += math.radians(random.uniform(-45, 45))
            if p['pos'][0] < min_x:
                p['pos'][0] = min_x
                p['angle'] = 0
                p['target_angle'] = random.uniform(-0.5, 0.5)
            elif p['pos'][0] > max_x:
                p['pos'][0] = max_x
                p['angle'] = math.pi
                p['target_angle'] = math.pi + random.uniform(-0.5, 0.5)
            if p['pos'][1] < min_y:
                p['pos'][1] = min_y
                p['angle'] = math.pi / 2
                p['target_angle'] = (math.pi / 2) + random.uniform(-0.5, 0.5)
            elif p['pos'][1] > max_y:
                p['pos'][1] = max_y
                p['angle'] = -math.pi / 2
                p['target_angle'] = (-math.pi / 2) + random.uniform(-0.5, 0.5)
            for other in self.planes:
                if other['id'] == p['id']: continue
                dx = other['pos'][0] - p['pos'][0]
                dy = other['pos'][1] - p['pos'][1]
                dist = (dx**2 + dy**2)**0.5
                if dist < Window.width * 0.14:
                    p['target_angle'] = math.atan2(-dy, -dx)
            angle_diff = (p['target_angle'] - p['angle'] + math.pi) % (2 * math.pi) - math.pi
            p['angle'] += max(-turn_speed, min(turn_speed, angle_diff))
            p['pos'][0] += p['speed'] * math.cos(p['angle']) * (dt * 60.0)
            p['pos'][1] += p['speed'] * math.sin(p['angle']) * (dt * 60.0)
        self.draw_radar_elements()

    def on_touch_down(self, touch):
        if self.game_state != "PLAYER_TURN":
            return super().on_touch_down(touch)
        click_radius = Window.width * 0.09
        for p in self.planes:
            if p['clicked']: continue
            distance = ((touch.x - p['pos'][0])**2 + (touch.y - p['pos'][1])**2)**0.5
            if distance <= click_radius:
                self.handle_plane_selection(p)
                return True
        return super().on_touch_down(touch)

    def handle_plane_selection(self, plane):
        expected_id = self.target_order[self.current_click_index]
        if plane['id'] == expected_id:
            plane['clicked'] = True
            self.current_click_index += 1
            self.draw_radar_elements()
            if self.current_click_index == len(self.target_order):
                self.game_state = "IDLE"
                self.status_label.text = "AIRSPACE CLEAR!"
                self.round_number += 1
                Clock.schedule_once(lambda dt: self.start_round(), 1.2)
        else:
            self.wrong_plane_id = plane['id']
            self.game_state = "GAME_OVER"
            trigger_haptic_feedback(0.08)
            if self.round_number > self.high_score:
                self.high_score = self.round_number
                self.save_high_score()
                self.status_label.text = f"NEW HIGH SCORE!\nREACHED ROUND {self.round_number}"
            else:
                self.status_label.text = "GAME OVER!"
            self.draw_radar_elements()
            self.render_plane_labels(reveal_all=True)
            self.start_btn.text = "RESTART RADAR"
            self.start_btn.background_color = (0.75, 0.2, 0.2, 1)
            if self.play_help_row not in self.layout.children:
                self.play_help_row.disabled = False
                self.layout.add_widget(self.play_help_row)
            if self.back_btn in self.layout.children:
                self.layout.remove_widget(self.back_btn)
            self.layout.add_widget(self.back_btn)
            self.score_label.text = f"ROUND: {self.round_number}  |  BEST: {self.high_score}"

    def render_plane_labels(self, reveal_all=False):
        self.clear_plane_labels()
        lbl_size = Scale.min_dim(0.08)
        
        for p in self.planes:
            if self.game_state == "COUNTDOWN" or reveal_all:
                lbl = Label(
                    text=str(p['id']), 
                    font_size=Scale.font(14), 
                    font_name='assets/fonts/ARCADE_N.TTF',
                    color=(0, 0.75, 1, 1) if not reveal_all else (1, 0.84, 0, 1), 
                    size_hint=(None, None),
                    size=(lbl_size, lbl_size), 
                    pos=(p['pos'][0] - (lbl_size / 2), p['pos'][1] + Scale.height_pct(0.04))
                )
                self.layout.add_widget(lbl)

    def clear_plane_labels(self):
        for child in list(self.layout.children):
            if isinstance(child, Label) and child not in [self.score_label, self.planes_count_label, self.status_label]:
                self.layout.remove_widget(child)

    def draw_radar_elements(self):
        self.canvas.remove_group('radar_shapes')
        if not self.planes: return
        with self.canvas:
            from kivy.graphics import Color, Mesh
            for p in self.planes:
                if p['clicked']:
                    Color(0.2, 0.2, 0.3, 0.4, group='radar_shapes')
                elif self.game_state == "GAME_OVER" and p['id'] == self.wrong_plane_id:
                    Color(0.9, 0.1, 0.1, 1, group='radar_shapes')
                else:
                    Color(1, 1, 1, 1, group='radar_shapes')
                w, h = Window.width * 0.05, Window.width * 0.05
                x, y = p['pos'][0], p['pos'][1]
                rad = p['angle']
                top_x = x + h * math.cos(rad)
                top_y = y + h * math.sin(rad)
                left_x = x + w * math.cos(rad + math.radians(145))
                left_y = y + w * math.sin(rad + math.radians(145))
                right_x = x + w * math.cos(rad - math.radians(145))
                right_y = y + w * math.sin(rad - math.radians(145))
                notch_x = x + (w * 0.25) * math.cos(rad + math.pi)
                notch_y = y + (w * 0.25) * math.sin(rad + math.pi)
                vertices = [top_x, top_y, 0, 0, left_x, left_y, 0, 0, notch_x, notch_y, 0, 0, right_x, right_y, 0, 0]
                indices = [0, 1, 2, 0, 2, 3]
                Mesh(vertices=vertices, indices=indices, mode='triangles', group='radar_shapes')

    def clear_radar_screen(self):
        self.clear_plane_labels()
        self.planes = []
        self.canvas.remove_group('radar_shapes')

class CodeCaptureScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.round_number = 1
        self.current_score = 4
        self.high_score = 0
        self.target_code = ""
        self.format_slots = 4
        self.shutter_open = True
        
        self.layout = RelativeLayout()
        self.add_widget(self.layout)
        
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        
        self.load_high_score()

        self.score_label = Label(
            text="SCORE: 4", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.28, 'center_y': 0.92}
        )
        self.layout.add_widget(self.score_label)
        
        self.round_label = Label(
            text="ROUND: 1", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.52, 'center_y': 0.92}
        )
        self.layout.add_widget(self.round_label)

        self.hi_score_label = Label(
            text=f"BEST: {self.high_score}", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.78, 'center_y': 0.92}
        )
        self.layout.add_widget(self.hi_score_label)
        
        self.barcode_widget = Widget(size_hint=(0.7, 0.12), pos_hint={'center_x': 0.5, 'center_y': 0.72})
        self.layout.add_widget(self.barcode_widget)
        self.barcode_widget.bind(pos=self.draw_barcode, size=self.draw_barcode)
        
        self.code_display = Label(
            text="0000", font_size='16sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 1, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.58}
        )
        self.layout.add_widget(self.code_display)
        
        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        
        # 🟢 ROW WRAPPER
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10), 
            size_hint=(0.9,0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), size_hint_x=0.8,
            background_normal='', background_color=(0, 0.75, 1, 1)
        )
        self.start_btn.bind(on_release=self.start_game)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size='16sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

        self.layout.add_widget(self.back_btn)

        self.shutter = RelativeLayout(size_hint=(1, 0.6), pos_hint={'x': 0, 'y': -0.6})
        with self.shutter.canvas.before:
            Color(0.12, 0.16, 0.32, 1)
            self.shutter_bg = Rectangle(pos=self.shutter.pos, size=self.shutter.size)
            Color(0, 0.75, 1, 1)
            self.shutter_line = Line(rectangle=(self.shutter.x, self.shutter.y, Window.width, Window.height * 0.6), width=dp(2))
        self.shutter.bind(pos=self.sync_shutter_canvas, size=self.sync_shutter_canvas)
        self.layout.add_widget(self.shutter)
        
        self.input_field_box = BoxLayout(orientation='horizontal', size_hint=(0.9, 0.12), pos_hint={'center_x': 0.5, 'top': 0.92}, spacing=dp(5))
        self.shutter.add_widget(self.input_field_box)
        
        self.numpad = GridLayout(cols=3, rows=4, spacing=dp(4), size_hint=(0.8, 0.68), pos_hint={'center_x': 0.5, 'y': 0.04})
        self.build_numpad()
        self.shutter.add_widget(self.numpad)
        
        self.shutter_handle = Button(
            text="PULL SHUTTER UP", font_size='10sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), size_hint=(0.6, 0.06), pos_hint={'center_x': 0.5, 'y': 0.0},
            background_normal='', background_color=(0, 0.75, 1, 1)
        )
        self.shutter_handle.bind(on_release=self.toggle_shutter)

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Code Capture"
        placeholders = [
            "Memorize the generated numeric code shown on your screen",
            "Pull up the terminal shutter to unveil the numpad",
            "Input the sequence perfectly and hit SUB to submit"
        ]
        overlay = InstructionOverlay(game_name=game_name, rules_list=placeholders, close_callback=self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def on_leave(self, *args):
        Animation.cancel_all(self.shutter)
        Animation.cancel_all(self.shutter_handle)
        self.clear_game_state()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def sync_shutter_canvas(self, instance, value):
        self.shutter_bg.pos = instance.pos
        self.shutter_bg.size = instance.size
        self.shutter_line.rectangle = (instance.x, instance.y, instance.width, instance.height)

    def draw_barcode(self, instance, *args):
        instance.canvas.clear()
        with instance.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=instance.pos, size=instance.size)
            local_rand = random.Random(self.round_number + 99)
            Color(0, 0, 0, 1)
            curr_x = instance.x + dp(10)
            end_limit = instance.right - dp(10)
            while curr_x < end_limit:
                line_w = local_rand.choice([dp(2), dp(4), dp(6)])
                Rectangle(pos=(curr_x, instance.y + dp(5)), size=(line_w, instance.height - dp(10)))
                curr_x += line_w + local_rand.choice([dp(2), dp(4)])

    def build_numpad(self):
        for digit in ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'CLR', '0', 'SUB']:
            btn = Button(
                text=digit, font_name='assets/fonts/ARCADE_N.TTF', font_size='18sp',
                background_normal='', background_color=(0.04, 0.06, 0.17, 1) if digit not in ['CLR','SUB'] else (0.8, 0.2, 0.2, 1) if digit=='CLR' else (0, 0.5, 0.8, 1)
            )
            btn.bind(on_release=self.handle_numpad_press)
            self.numpad.add_widget(btn)

    def go_back_to_menu(self, instance):
        Animation.cancel_all(self.shutter)
        Animation.cancel_all(self.shutter_handle)
        self.clear_game_state()
        self.manager.current = 'menu'

    def clear_game_state(self):
        self.round_number = 1
        self.shutter.pos_hint = {'x': 0, 'y': -0.6}
        self.shutter_handle.pos_hint = {'center_x': 0.5, 'y': 0.0}
        self.shutter_open = True
        self.shutter_handle.text = "PULL SHUTTER UP"
        if self.shutter_handle in self.layout.children:
            self.layout.remove_widget(self.shutter_handle)
        if self.play_help_row not in self.layout.children:
            self.layout.add_widget(self.play_help_row)
        self.start_btn.text = "START GAME"
        self.play_help_row.disabled = False

    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('code_capture_high', 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['code_capture_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def start_game(self, instance):
        self.layout.remove_widget(self.play_help_row)
        if self.shutter_handle not in self.layout.children:
            self.layout.add_widget(self.shutter_handle)
        self.round_number = 1
        self.current_score = 4
        self.start_round()

    def start_round(self):
        self.score_label.text = f"SCORE: {self.current_score}"
        self.round_label.text = f"ROUND: {self.round_number}"
        self.hi_score_label.text = f"BEST: {self.high_score}"
        self.format_slots = 4 + (((self.round_number - 1) // 3) * 2)
        if self.format_slots > 16: self.format_slots = 16
        self.generate_formatted_code()
        self.build_input_text_fields()
        self.draw_barcode(self.barcode_widget)
        if not self.shutter_open:
            self.toggle_shutter(None)

    def generate_formatted_code(self):
        raw_digits = "".join([str(random.randint(0, 9)) for _ in range(self.format_slots)])
        self.target_code = raw_digits
        if self.format_slots == 4: self.code_display.text = raw_digits
        elif self.format_slots == 6: self.code_display.text = f"{raw_digits[:3]}-{raw_digits[3:]}"
        elif self.format_slots == 8: self.code_display.text = f"{raw_digits[:4]}-{raw_digits[4:]}"
        elif self.format_slots == 10: self.code_display.text = f"{raw_digits[:3]}-{raw_digits[3:6]}-{raw_digits[6:]}"
        elif self.format_slots == 12: self.code_display.text = f"{raw_digits[:4]}-{raw_digits[4:8]}-{raw_digits[8:]}"
        elif self.format_slots == 14: self.code_display.text = f"{raw_digits[:4]}-{raw_digits[4:8]}-{raw_digits[8:12]}-{raw_digits[12:]}"
        elif self.format_slots == 16: self.code_display.text = f"{raw_digits[:4]}-{raw_digits[4:8]}-{raw_digits[8:12]}-{raw_digits[12:]}"

    def build_input_text_fields(self):
        self.input_field_box.clear_widgets()
        self.text_inputs_list = []
        display_str = self.code_display.text
        for char in display_str:
            if char == "-":
                dash_lbl = Label(text="-", font_size='18sp', font_name='assets/fonts/ARCADE_N.TTF', color=(0, 0.75, 1, 1), size_hint=(None, 1), width=dp(10))
                self.input_field_box.add_widget(dash_lbl)
            else:
                ti = TextInput(
                    text="", font_name='assets/fonts/ARCADE_N.TTF', font_size='12sp',
                    halign='center', readonly=True, disabled=False,
                    background_normal='', background_color=(0.04, 0.06, 0.17, 1), foreground_color=(1, 1, 1, 1)
                )
                self.input_field_box.add_widget(ti)
                self.text_inputs_list.append(ti)

    def toggle_shutter(self, instance):
        if self.shutter_open:
            anim_shutter = Animation(pos_hint={'x': 0, 'y': 0}, duration=0.3, t='out_quad')
            anim_handle = Animation(pos_hint={'center_x': 0.5, 'y': 0.6}, duration=0.3, t='out_quad')
            self.shutter_handle.text = "DOWN (PENALTY)"
            self.shutter_open = False
        else:
            anim_shutter = Animation(pos_hint={'x': 0, 'y': -0.6}, duration=0.3, t='out_quad')
            anim_handle = Animation(pos_hint={'center_x': 0.5, 'y': 0.0}, duration=0.3, t='out_quad')
            self.shutter_handle.text = "PULL SHUTTER UP"
            self.shutter_open = True
            if instance is not None:
                self.current_score = max(0, self.current_score - 1)
                self.score_label.text = f"SCORE: {self.current_score}"
        anim_shutter.start(self.shutter)
        anim_handle.start(self.shutter_handle)

    def handle_numpad_press(self, instance):
        val = instance.text
        current_inputs_text = [ti.text for ti in self.text_inputs_list]
        empty_index = current_inputs_text.index("") if "" in current_inputs_text else -1
        if val == "CLR":
            for ti in self.text_inputs_list: ti.text = ""
        elif val == "SUB":
            self.verify_submission()
        else:
            if empty_index != -1 and not self.shutter_open:
                self.text_inputs_list[empty_index].text = val

    def verify_submission(self):
        user_code = "".join([ti.text for ti in self.text_inputs_list])
        if user_code == self.target_code and not self.shutter_open:
            self.current_score += 4
            self.round_number += 1
            self.start_round()
        else:
            trigger_haptic_feedback(0.08)
            if self.current_score > self.high_score:
                self.high_score = self.current_score
                self.save_high_score()
                self.code_display.text = f"NEW BEST: {self.current_score}!"
                self.code_display.color = (1, 0.84, 0, 1)
            else:
                self.code_display.text = "CRITICAL FAIL!"
                self.code_display.color = (0.9, 0.2, 0.2, 1)
            self.clear_game_state()
            self.start_btn.text = "RETRY CAPTURE"
            self.start_btn.background_color = (0.75, 0.2, 0.2, 1)

class PointVelocityScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.score = 0
        self.high_score = 0
        self.time_remaining = 60
        self.game_active = False
        
        self.triangles = []  
        self.directions = ['UP', 'DOWN', 'LEFT', 'RIGHT']
        self.timer_event = None
        self.physics_event = None
        self.touch_start_pos = None
        self.text_flash_timer = 0.0

        self.current_color = 'RED'
        self.current_point_dir = 'UP'
        self.current_move_dir = 'RIGHT'

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.load_high_score()

        self.title_label = Label(
            text="SWIPE FOCUS", font_size=Scale.font(30), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.90}
        )
        self.layout.add_widget(self.title_label)

        self.timer_label = Label(
            text="TIME: 60s", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.80}
        )
        self.layout.add_widget(self.timer_label)

        self.score_label = Label(
            text="SCORE: 0 |", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.34, 'center_y': 0.85}
        )
        self.layout.add_widget(self.score_label)

        self.hi_score_label = Label(
            text=f"BEST: {self.high_score}", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.67, 'center_y': 0.85}
        )
        self.layout.add_widget(self.hi_score_label)

        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        # 🟢 ROW WRAPPER
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10), 
            size_hint=(0.9,0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), size_hint_x=0.8,
            background_normal='', background_color=(0, 0.75, 1, 1)
        )
        self.start_btn.bind(on_release=self.trigger_countdown)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size='16sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Point Velocity"
        placeholders = [
            "Green Triangles: Swipe in the direction they are pointing",
            "Red Triangles: Swipe in the direction they are moving"
        ]
        overlay = InstructionOverlay(game_name=game_name, rules_list=placeholders, close_callback=self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def on_enter(self):
        Window.bind(on_key_down=self.handle_keyboard_input)

    def on_leave(self):
        Window.unbind(on_key_down=self.handle_keyboard_input)
        self.stop_game_engine()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.draw_velocity_shapes()

    def go_back_to_menu(self, instance):
        self.stop_game_engine()
        self.manager.current = 'menu'

    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('point_velocity_high', 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['point_velocity_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def trigger_countdown(self, instance):
        self.layout.remove_widget(self.play_help_row)
        self.score = 0
        self.time_remaining = 60
        self.score_label.text = "SCORE: 0 |"
        self.timer_label.text = "TIME: 60s"
        self.hi_score_label.text = f"BEST: {self.high_score}"
        self.triangles = []
        self.canvas.remove_group('velocity_shapes')
        self.countdown_ticks = 3
        self.title_label.text = str(self.countdown_ticks)
        Clock.schedule_interval(self.handle_countdown_tick, 1.0)

    def handle_countdown_tick(self, dt):
        self.countdown_ticks -= 1
        if self.countdown_ticks > 0:
            self.title_label.text = str(self.countdown_ticks)
        else:
            self.title_label.text = "SWIPE FOCUS"
            Clock.unschedule(self.handle_countdown_tick)
            self.start_game()

    def start_game(self):
        self.game_active = True
        self.roll_global_rule_state()
        self.populate_fluid_stream_pool()
        self.physics_event = Clock.schedule_interval(self.update_physics, 1.0 / 60.0)
        self.timer_event = Clock.schedule_interval(self.handle_clock_tick, 1.0)

    def roll_global_rule_state(self):
        self.current_color = random.choice(['RED', 'GREEN'])
        self.current_point_dir = random.choice(self.directions)
        self.current_move_dir = random.choice(self.directions)

    def populate_fluid_stream_pool(self):
        self.triangles = []
        for _ in range(10):
            self.triangles.append({
                'pos': [random.uniform(0, Window.width), random.uniform(Window.height * 0.12, Window.height * 0.58)],
                'color': self.current_color, 'point_dir': self.current_point_dir, 'move_dir': self.current_move_dir, 'opacity': random.uniform(0.7, 1.0)
            })

    def update_physics(self, dt):
        if not self.game_active: return
        if self.text_flash_timer > 0:
            self.text_flash_timer -= dt
            if self.text_flash_timer <= 0:
                self.timer_label.color = (0, 0.75, 1, 1)
                self.score_label.color = (0, 0.75, 1, 1)
                self.hi_score_label.color = (0, 0.75, 1, 1)
        speed = Window.width * 0.015 * (dt * 60.0)
        for t in self.triangles:
            if t['move_dir'] == 'UP': t['pos'][1] += speed
            elif t['move_dir'] == 'DOWN': t['pos'][1] -= speed
            elif t['move_dir'] == 'LEFT': t['pos'][0] -= speed
            elif t['move_dir'] == 'RIGHT': t['pos'][0] += speed
            if t['pos'][0] < -20: t['pos'][0] = Window.width + 20
            elif t['pos'][0] > Window.width + 20: t['pos'][0] = -20
            if t['pos'][1] < Window.height * 0.10: t['pos'][1] = Window.height * 0.58
            elif t['pos'][1] > Window.height * 0.58: t['pos'][1] = Window.height * 0.10
        self.draw_velocity_shapes()

    def on_touch_down(self, touch):
        if self.back_btn.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if not self.game_active:
            return super().on_touch_down(touch)
        self.touch_start_pos = touch.pos
        return True

    def on_touch_up(self, touch):
        if self.back_btn.collide_point(*touch.pos):
            return super().on_touch_up(touch)
        if not self.game_active or not self.touch_start_pos:
            return super().on_touch_up(touch)
        dx = touch.x - self.touch_start_pos[0]
        dy = touch.y - self.touch_start_pos[1]
        min_swipe_threshold = dp(20)
        if (dx**2 + dy**2)**0.5 < min_swipe_threshold:
            return super().on_touch_up(touch)
        if abs(dx) > abs(dy):
            swipe_dir = 'RIGHT' if dx > 0 else 'LEFT'
        else:
            swipe_dir = 'UP' if dy > 0 else 'DOWN'
        self.evaluate_directional_input(swipe_dir)
        self.touch_start_pos = None
        return True

    def handle_keyboard_input(self, window, key, scancode, codepoint, modifier):
        if not self.game_active: return
        key_map = {119: 'UP', 115: 'DOWN', 97: 'LEFT', 100: 'RIGHT'} 
        if key in key_map:
            self.evaluate_directional_input(key_map[key])

    def evaluate_directional_input(self, user_direction):
        correct_target = self.current_point_dir if self.current_color == 'GREEN' else self.current_move_dir
        if user_direction == correct_target:
            self.score += 1
            self.score_label.text = f"SCORE: {self.score} |"
            self.roll_global_rule_state()
            for t in self.triangles:
                t['color'] = self.current_color
                t['point_dir'] = self.current_point_dir
                t['move_dir'] = self.current_move_dir
        else:
            trigger_haptic_feedback(0.08)
            self.time_remaining = max(0, self.time_remaining - 1)
            self.timer_label.text = f"TIME: {self.time_remaining}s"
            self.timer_label.color = (0.9, 0.2, 0.2, 1)
            self.score_label.color = (0.9, 0.2, 0.2, 1)
            self.hi_score_label.color = (0.9, 0.2, 0.2, 1)
            self.text_flash_timer = 0.35  
            self.roll_global_rule_state()
            for t in self.triangles:
                t['color'] = self.current_color
                t['point_dir'] = self.current_point_dir
                t['move_dir'] = self.current_move_dir

    def draw_velocity_shapes(self):
        self.canvas.remove_group('velocity_shapes')
        if not self.triangles or not self.game_active: return
        with self.canvas:
            for t in self.triangles:
                if t['color'] == 'GREEN': Color(0.1, 0.7, 0.3, t['opacity'], group='velocity_shapes')
                else: Color(0.9, 0.2, 0.2, t['opacity'], group='velocity_shapes')
                x, y = t['pos'][0], t['pos'][1]
                size = Window.width * 0.035
                if t['point_dir'] == 'UP': vertices = [x, y + size, 0, 0,  x - size, y - size, 0, 0,  x + size, y - size, 0, 0]
                elif t['point_dir'] == 'DOWN': vertices = [x, y - size, 0, 0,  x - size, y + size, 0, 0,  x + size, y + size, 0, 0]
                elif t['point_dir'] == 'LEFT': vertices = [x - size, y, 0, 0,  x + size, y + size, 0, 0,  x + size, y - size, 0, 0]
                else: vertices = [x + size, y, 0, 0,  x - size, y + size, 0, 0,  x - size, y - size, 0, 0]
                indices = [0, 1, 2]
                Mesh(vertices=vertices, indices=indices, mode='triangles', group='velocity_shapes')

    def handle_clock_tick(self, dt):
        self.time_remaining -= 1
        if self.time_remaining > 0:
            self.timer_label.text = f"TIME: {self.time_remaining}s"
        else:
            self.stop_game_engine()

    def stop_game_engine(self):
        record_jbrcade_game_score("point_velocity", self.score)
        self.game_active = False
        if self.timer_event: Clock.unschedule(self.timer_event); self.timer_event = None
        if self.physics_event: Clock.unschedule(self.physics_event); self.physics_event = None
        Clock.unschedule(self.handle_countdown_tick)
        self.canvas.remove_group('velocity_shapes')
        self.timer_label.color = (0, 0.75, 1, 1)
        self.score_label.color = (0, 0.75, 1, 1)
        self.hi_score_label.color = (0, 0.75, 1, 1)
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
            self.title_label.text = "NEW HIGH SCORE!"
            self.title_label.color = (1, 0.84, 0, 1)
        else:
            self.title_label.text = "TIME UP!"
            self.title_label.color = (0, 0.75, 1, 1)
        #self.timer_label.text = f"FINAL SCORE: {self.score}"
        self.hi_score_label.text = f"BEST: {self.high_score}"
        if self.play_help_row not in self.layout.children:
            self.start_btn.text = "PLAY AGAIN"
            self.play_help_row.disabled = False
            self.layout.add_widget(self.play_help_row)

class ConsecutiveShapesScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.score = 0
        self.high_score = 0
        self.time_remaining = 60
        self.game_active = False
        self.penalty_active = False
        
        self.shape_profiles = [
            {'type': 'SQUARE', 'color': (0.9, 0.2, 0.2, 1)},      
            {'type': 'TRIANGLE', 'color': (0.1, 0.7, 0.3, 1)},    
            {'type': 'CIRCLE', 'color': (0, 0.6, 0.9, 1)},        
            {'type': 'DIAMOND', 'color': (0.9, 0.7, 0, 1)},       
            {'type': 'CROSS', 'color': (0.6, 0.2, 0.8, 1)}        
        ]
        self.cards_in_play = []  
        self.previous_shape_type = None
        self.current_shape_type = None
        self.timer_event = None
        self.physics_event = None
        self.flash_red_btn = None

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.load_high_score()

        self.title_label = Label(
            text="MATCH PREVIOUS SHAPE?", font_size='14sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.90}
        )
        self.layout.add_widget(self.title_label)

        self.timer_label = Label(
            text="TIME: 60s", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.76}
        )
        self.layout.add_widget(self.timer_label)

        self.score_label = Label(
            text="SCORE: 0", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.3, 'center_y': 0.83}
        )
        self.layout.add_widget(self.score_label)

        self.hi_score_label = Label(
            text=f"BEST: {self.high_score}", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.7, 'center_y': 0.83}
        )
        self.layout.add_widget(self.hi_score_label)

        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        self.yes_btn = Button(
            text="Y", font_size='22sp', font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.28, 0.10), pos_hint={'x': 0.18, 'y': 0.14},
            background_normal='', background_color=(0, 0.6, 0.3, 1)
        )
        self.yes_btn.bind(on_release=lambda x: self.process_match_submission(True, self.yes_btn))

        self.no_btn = Button(
            text="N", font_size='22sp', font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.28, 0.10), pos_hint={'x': 0.54, 'y': 0.14},
            background_normal='', background_color=(0.75, 0.15, 0.15, 1)
        )
        self.no_btn.bind(on_release=lambda x: self.process_match_submission(False, self.no_btn))

        # 🟢 ROW WRAPPER
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10), 
            size_hint=(0.9,0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), size_hint_x=0.8,
            background_normal='', background_color=(0, 0.75, 1, 1)
        )
        self.start_btn.bind(on_release=self.trigger_countdown)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size='16sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Consecutive Shapes"
        placeholders = [
            "Memorize the shape currently resting on your screen",
            "When the cards shift, evaluate if the incoming shape matches it",
            "Press Y for a matching shape or N if it differs"
        ]
        overlay = InstructionOverlay(game_name=game_name, rules_list=placeholders, close_callback=self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def on_leave(self, *args):
        self.stop_game_engine()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def go_back_to_menu(self, instance):
        self.stop_game_engine()
        self.manager.current = 'menu'

    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('consecutive_shapes_high', 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['consecutive_shapes_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def trigger_countdown(self, instance):
        self.layout.remove_widget(self.play_help_row)
        self.score = 0
        self.time_remaining = 60
        self.score_label.text = "SCORE: 0"
        self.timer_label.text = "TIME: 60s"
        self.hi_score_label.text = f"BEST: {self.high_score}"
        self.title_label.text = "MATCH PREVIOUS SHAPE?"
        self.clear_active_cards()
        self.countdown_ticks = 3
        self.title_label.text = f"MEMORIZE: {self.countdown_ticks}"
        self.spawn_new_card(initial_center=True)
        Clock.schedule_interval(self.handle_countdown_tick, 1.0)

    def handle_countdown_tick(self, dt):
        self.countdown_ticks -= 1
        if self.countdown_ticks > 0:
            self.title_label.text = f"MEMORIZE: {self.countdown_ticks}"
        else:
            Clock.unschedule(self.handle_countdown_tick)
            self.title_label.text = "MATCH PREVIOUS SHAPE?"
            self.start_game_loop()

    def start_game_loop(self):
        self.game_active = True
        self.penalty_active = False
        if self.yes_btn not in self.layout.children: self.layout.add_widget(self.yes_btn)
        if self.no_btn not in self.layout.children: self.layout.add_widget(self.no_btn)
        self.yes_btn.background_color = (0, 0.6, 0.3, 1)
        self.no_btn.background_color = (0.75, 0.15, 0.15, 1)
        self.cycle_next_round_cards()
        self.physics_event = Clock.schedule_interval(self.update_card_translations, 1.0 / 60.0)
        self.timer_event = Clock.schedule_interval(self.handle_clock_tick, 1.0)

    def spawn_new_card(self, initial_center=False):
        if initial_center or self.previous_shape_type is None:
            chosen_profile = random.choice(self.shape_profiles)
        else:
            should_match = random.choice([True, False])
            if should_match:
                matching_profiles = [p for p in self.shape_profiles if p['type'] == self.previous_shape_type]
                chosen_profile = random.choice(matching_profiles)
            else:
                mismatch_profiles = [p for p in self.shape_profiles if p['type'] != self.previous_shape_type]
                chosen_profile = random.choice(mismatch_profiles)
        card_layout = RelativeLayout(size_hint=(None, None), size=(Window.width * 0.40, Window.width * 0.40))
        if initial_center:
            card_layout.pos_hint = {'center_x': 0.5, 'center_y': 0.48}
            self.current_shape_type = chosen_profile['type']
        else:
            card_layout.pos = (Window.width, Window.height * 0.48 - card_layout.height / 2)
        with card_layout.canvas.before:
            Color(1, 1, 1, 1)
            card_bg = Rectangle(pos=(0, 0), size=card_layout.size)
        card_layout.bind(size=lambda inst, val: setattr(card_bg, 'size', val))
        with card_layout.canvas:
            Color(*chosen_profile['color'])
            s_size = Window.width * 0.10
            cx, cy = Window.width * 0.20, Window.width * 0.20 
            stype = chosen_profile['type']
            if stype == 'SQUARE': Rectangle(pos=(cx - s_size/2, cy - s_size/2), size=(s_size, s_size))
            elif stype == 'TRIANGLE': Mesh(vertices=[cx, cy + s_size/2, 0,0,  cx - s_size/2, cy - s_size/2, 0,0,  cx + s_size/2, cy - s_size/2, 0,0], indices=[0,1,2], mode='triangles')
            elif stype == 'CIRCLE': Ellipse(pos=(cx - s_size/2, cy - s_size/2), size=(s_size, s_size))
            elif stype == 'DIAMOND': Mesh(vertices=[cx, cy + s_size/2, 0,0,  cx - s_size/2, cy, 0,0,  cx, cy - s_size/2, 0,0,  cx + s_size/2, cy, 0,0], indices=[0,1,2, 0,2,3], mode='triangles')
            elif stype == 'CROSS':
                Rectangle(pos=(cx - s_size/6, cy - s_size/2), size=(s_size/3, s_size))
                Rectangle(pos=(cx - s_size/2, cy - s_size/6), size=(s_size, s_size/3))
        self.layout.add_widget(card_layout)
        self.cards_in_play.append({'layout': card_layout, 'shape': chosen_profile, 'target_x': Window.width * 0.5 - card_layout.width / 2})

    def cycle_next_round_cards(self):
        self.previous_shape_type = self.current_shape_type
        for c_data in self.cards_in_play:
            c_data['target_x'] = -c_data['layout'].width - dp(20)
            c_data['layout'].pos_hint = {}
        self.spawn_new_card(initial_center=False)
        self.current_shape_type = self.cards_in_play[-1]['shape']['type']

    def update_card_translations(self, dt):
        if not self.game_active: return
        slide_speed = Window.width * 0.08 * (dt * 60.0)
        cards_to_remove = []
        for c_data in self.cards_in_play:
            layout = c_data['layout']
            target_x = c_data['target_x']
            if abs(layout.x - target_x) > slide_speed:
                if layout.x < target_x: layout.x += slide_speed
                else: layout.x -= slide_speed
            else: layout.x = target_x
            if target_x < 0 and layout.right <= 0:
                cards_to_remove.append(c_data)
        for old_card in cards_to_remove:
            self.layout.remove_widget(old_card['layout'])
            self.cards_in_play.remove(old_card)

    def process_match_submission(self, user_pressed_yes, clicked_button):
        if not self.game_active or self.penalty_active: return
        is_true_match = (self.current_shape_type == self.previous_shape_type)
        if user_pressed_yes == is_true_match:
            self.score += 1
            self.score_label.text = f"SCORE: {self.score}"
            self.cycle_next_round_cards()
        else:
            trigger_haptic_feedback(0.08)
            self.penalty_active = True
            self.flash_red_btn = clicked_button
            self.flash_red_btn.background_color = (0.5, 0.15, 0.15, 1)
            Clock.schedule_once(self.lift_penalty_cooldown, 1.0)

    def lift_penalty_cooldown(self, dt):
        if self.flash_red_btn:
            if self.flash_red_btn == self.yes_btn: self.flash_red_btn.background_color = (0, 0.6, 0.3, 1)
            else: self.flash_red_btn.background_color = (0.75, 0.15, 0.15, 1)
        self.penalty_active = False
        self.flash_red_btn = None
        if self.game_active: self.cycle_next_round_cards()

    def handle_clock_tick(self, dt):
        self.time_remaining -= 1
        if self.time_remaining > 0: self.timer_label.text = f"TIME: {self.time_remaining}s"
        else: self.stop_game_engine()

    def clear_active_cards(self):
        for c_data in self.cards_in_play: self.layout.remove_widget(c_data['layout'])
        self.cards_in_play = []

    def stop_game_engine(self):
        self.game_active = False
        self.penalty_active = False
        Clock.unschedule(self.lift_penalty_cooldown)
        if self.timer_event: Clock.unschedule(self.timer_event); self.timer_event = None
        if self.physics_event: Clock.unschedule(self.physics_event); self.physics_event = None
        Clock.unschedule(self.handle_countdown_tick)
        self.clear_active_cards()
        self.layout.remove_widget(self.yes_btn)
        self.layout.remove_widget(self.no_btn)
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
            self.title_label.text = "NEW HIGH SCORE!"
            self.title_label.color = (1, 0.84, 0, 1)
        else:
            self.title_label.text = "TIME UP!"
            self.title_label.color = (0, 0.75, 1, 1)
        #self.timer_label.text = f"FINAL SCORE: {self.score}"
        self.hi_score_label.text = f"BEST: {self.high_score}"
        if self.play_help_row not in self.layout.children:
            self.start_btn.text = "PLAY AGAIN"
            self.play_help_row.disabled = False
            self.layout.add_widget(self.play_help_row)

class MatrixRecallScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.round_number = 1
        self.score = 0
        self.high_score = 0  
        self.time_remaining = 30  
        self.game_active = False
        
        self.cols_count = 5
        self.rows_count = 5
        self.active_targets = []  
        self.user_selections = []  
        self.tiles_list = []      
        self.timer_event = None
        self.countdown_event = None

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.load_high_score()

        self.title_label = Label(
            text="MATRIX RECALL", font_size=Scale.font(30), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.92}
        )
        self.layout.add_widget(self.title_label)

        self.timer_label = Label(
            text="TIME: 1:00", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.80}
        )
        self.layout.add_widget(self.timer_label)

        self.score_label = Label(
            text="SCORE: 0", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.3, 'center_y': 0.86}
        )
        self.layout.add_widget(self.score_label)

        self.hi_score_label = Label(
            text=f"BEST: {self.high_score}", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.7, 'center_y': 0.86}
        )
        self.layout.add_widget(self.hi_score_label)

        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        self.grid_container = RelativeLayout(size_hint=(0.85, 0.46), pos_hint={'center_x': 0.5, 'center_y': 0.40})
        self.layout.add_widget(self.grid_container)

        with self.grid_container.canvas.before:
            Color(0, 0.75, 1, 1)  
            self.grid_lines_group = InstructionGroup()
            self.grid_container.canvas.before.add(self.grid_lines_group)

        self.matrix_grid = None

        # 🟢 ROW WRAPPER
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10), 
            size_hint=(0.9,0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), size_hint_x=0.8,
            background_normal='', background_color=(0, 0.75, 1, 1)
        )
        self.start_btn.bind(on_release=self.start_game)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size='16sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Matrix Recall"
        placeholders = [
            "Memorize the lit grid tile locations",
            "The board will reset to clean blank tiles",
            "Tap exclusively those specific tiles from memory"
        ]
        overlay = InstructionOverlay(game_name=game_name, rules_list=placeholders, close_callback=self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def on_leave(self, *args):
        self.stop_game_engine()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def go_back_to_menu(self, instance):
        self.stop_game_engine()
        self.manager.current = 'menu'

    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('matrix_recall_high', 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['matrix_recall_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def start_game(self, instance):
        self.layout.remove_widget(self.play_help_row)
        self.round_number = 1
        self.score = 0
        self.time_remaining = 30  
        self.score_label.text = "SCORE: 0"
        self.hi_score_label.text = f"BEST: {self.high_score}"
        self.title_label.text = "MATRIX RECALL"
        self.title_label.color = (0, 0.75, 1, 1)
        self.start_round()
        if self.timer_event: Clock.unschedule(self.timer_event)
        self.timer_event = Clock.schedule_interval(self.handle_game_clock_tick, 1.0)

    def start_round(self):
        self.user_selections = []
        self.game_active = False
        phase = (self.round_number - 1) // 3
        if phase % 2 == 0:
            self.cols_count = 5 + (phase // 2)
            self.rows_count = 5 + (phase // 2)
        else:
            self.cols_count = 5 + (phase // 2) + 1
            self.rows_count = 5 + (phase // 2)
        rem = self.round_number % 3
        if rem == 1: pct = 0.40  
        elif rem == 2: pct = 0.50  
        else: pct = 0.60  
        total_cells = self.cols_count * self.rows_count
        target_count = max(1, int(total_cells * pct))
        self.grid_container.clear_widgets()
        self.grid_lines_group.clear()
        self.tiles_list = []
        self.matrix_grid = GridLayout(cols=self.cols_count, rows=self.rows_count, spacing=dp(4), size_hint=(1, 1))
        self.grid_container.add_widget(self.matrix_grid)
        for idx in range(total_cells):
            tile_btn = Button(text="", background_normal='', background_color=(0, 0.75, 1, 1))
            tile_btn.tile_index = idx
            tile_btn.bind(on_release=self.handle_tile_press)
            self.matrix_grid.add_widget(tile_btn)
            self.tiles_list.append(tile_btn)
        Clock.schedule_once(self.draw_wireframe_lines, 0.05)
        self.active_targets = random.sample(range(total_cells), target_count)
        for target_idx in self.active_targets: self.tiles_list[target_idx].background_color = (1, 0.85, 0, 1) 
        self.countdown_ticks = 3
        self.title_label.text = f"MEMORIZE: {self.countdown_ticks}s"
        if self.countdown_event: Clock.unschedule(self.countdown_event)
        self.countdown_event = Clock.schedule_interval(self.handle_memorize_tick, 1.0)
        
    def handle_memorize_tick(self, dt):
        self.countdown_ticks -= 1
        if self.countdown_ticks > 0: self.title_label.text = f"MEMORIZE: {self.countdown_ticks}s"
        else:
            Clock.unschedule(self.countdown_event)
            self.countdown_event = None
            self.title_label.text = "RECALL TILES!"
            self.reveal_blank_board()

    def draw_wireframe_lines(self, dt):
        if not self.matrix_grid or not self.tiles_list: return
        self.grid_lines_group.clear()
        for tile in self.tiles_list:
            abs_pos = self.matrix_grid.to_parent(tile.x, tile.y, relative=True)
            self.grid_lines_group.add(Line(rectangle=(abs_pos[0], abs_pos[1], tile.width, tile.height), width=dp(1)))

    def reveal_blank_board(self):
        for tile in self.tiles_list: tile.background_color = (0, 0, 0, 0)
        self.game_active = True

    def handle_tile_press(self, instance):
        if not self.game_active: return
        idx = instance.tile_index
        if idx in self.user_selections: return
        if idx in self.active_targets:
            instance.background_color = (1, 0.85, 0, 1)
            self.user_selections.append(idx)
            self.score += 1
            self.score_label.text = f"SCORE: {self.score}"
            if len(self.user_selections) == len(self.active_targets):
                self.game_active = False
                self.title_label.text = "PERFECT RECIPE!"
                self.round_number += 1
                self.time_remaining += 30
                self.update_timer_display_text()
                Clock.schedule_once(lambda dt: self.start_round(), 1.2)
        else:
            trigger_haptic_feedback(0.08)
            instance.background_color = (0.8, 0.15, 0.15, 1) 
            nearest_target_idx = self.calculate_nearest_correct_tile(idx)
            if nearest_target_idx is not None:
                self.tiles_list[nearest_target_idx].background_color = (1, 0.85, 0, 1)
                self.user_selections.append(nearest_target_idx)
                if len(self.user_selections) == len(self.active_targets):
                    self.game_active = False
                    self.title_label.text = "ROUND COMPLETE"
                    self.round_number += 1
                    self.time_remaining += 60
                    self.update_timer_display_text()
                    Clock.schedule_once(lambda dt: self.start_round(), 1.2)

    def calculate_nearest_correct_tile(self, wrong_idx):
        wrong_r = wrong_idx // self.cols_count
        wrong_c = wrong_idx % self.cols_count
        nearest_idx = None
        min_distance = float('inf')
        for t_idx in self.active_targets:
            if t_idx in self.user_selections: continue 
            t_r = t_idx // self.cols_count
            t_c = t_idx % self.cols_count
            distance = ((t_r - wrong_r)**2 + (t_c - wrong_c)**2)**0.5
            if distance < min_distance:
                min_distance = distance
                nearest_idx = t_idx
        return nearest_idx

    def handle_game_clock_tick(self, dt):
        self.time_remaining -= 1
        if self.time_remaining > 0: self.update_timer_display_text()
        else: self.stop_game_engine()

    def update_timer_display_text(self):
        mins = self.time_remaining // 60
        secs = self.time_remaining % 60
        self.timer_label.text = f"TIME: {mins}:{secs:02d}"

    def stop_game_engine(self):
        self.game_active = False
        if self.timer_event: Clock.unschedule(self.timer_event); self.timer_event = None
        if self.countdown_event: Clock.unschedule(self.countdown_event); self.countdown_event = None
        self.grid_container.clear_widgets()
        self.grid_lines_group.clear()
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
            self.title_label.text = "NEW HIGH SCORE!"
            self.title_label.color = (1, 0.84, 0, 1)
        else:
            self.title_label.text = "TIME UP!"
            self.title_label.color = (0, 0.75, 1, 1)
        self.timer_label.text = "TIME: 0:00"
        self.hi_score_label.text = f"BEST: {self.high_score}"
        if self.play_help_row not in self.layout.children:
            self.start_btn.text = "RESTART"
            self.play_help_row.disabled = False
            self.layout.add_widget(self.play_help_row) 

class RotationalMazeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.round_number = 1
        self.score = 0
        self.high_score = 1  
        self.time_remaining = 60  
        self.game_active = False
        self.grid_size = 15  
        self.maze_matrix = []  
        self.player_grid_pos = [1, 1]  
        self.exit_grid_pos = [13, 13]
        self.current_rotation_angle = 0  
        self.timer_event = None
        self.rotation_event = None

        self.maze_display_size = Window.width * 0.45  
        self.maze_y_position = 0.52  

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.load_high_score()

        self.title_label = Label(
            text="ROTATIONAL MAZE", font_size='16sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.9}
        )
        self.layout.add_widget(self.title_label)

        self.timer_label = Label(
            text="TIME: 60s", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.8}
        )
        self.layout.add_widget(self.timer_label)

        self.score_label = Label(
            text="SCORE: 0", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.3, 'center_y': 0.85}
        )
        self.layout.add_widget(self.score_label)

        self.hi_score_label = Label(
            text=f"BEST: ROUND {self.high_score}", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.7, 'center_y': 0.85}
        )
        self.layout.add_widget(self.hi_score_label)

        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        self.maze_container = RelativeLayout(
            size_hint=(None, None), size=(self.maze_display_size, self.maze_display_size), 
            pos_hint={'center_x': 0.5, 'center_y': self.maze_y_position}
        )
        self.layout.add_widget(self.maze_container)

        with self.maze_container.canvas.before:
            self.push_matrix = PushMatrix()
            self.rotation_instruction = Rotate(angle=0, origin=(self.maze_display_size / 2, self.maze_display_size / 2))
        with self.maze_container.canvas.after:
            self.pop_matrix = PopMatrix()

        self.build_control_keypad()

        # 🟢 ROW WRAPPER
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10), 
            size_hint=(0.9,0.1),
            pos_hint={'center_x': 0.5, 'center_y': self.maze_y_position}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), size_hint_x=0.8,
            background_normal='', background_color=(0, 0.75, 1, 1)
        )
        self.start_btn.bind(on_release=self.start_game)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size='14sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Rotational Maze"
        placeholders = [
            "Navigate your green dot safely towards the gold exit square",
            "The maze rotates every 3 seconds, but your controls remain the same",
            "A red triangle is embedded in the north wall of the maze",
            "Make use of this red triangle to reorient yourself"
        ]
        overlay = InstructionOverlay(game_name=game_name, rules_list=placeholders, close_callback=self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def on_leave(self, *args):
        self.stop_game_engine()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def go_back_to_menu(self, instance):
        self.stop_game_engine()
        self.manager.current = 'menu'

    def build_control_keypad(self):
        k_layout = RelativeLayout(size_hint=(1, 0.22), pos_hint={'x': 0, 'y': 0.01})
        self.layout.add_widget(k_layout)
        btn_sz = (0.15, 0.38)
        self.up_btn = Button(text="^", font_name='assets/fonts/ARCADE_N.TTF', size_hint=btn_sz, pos_hint={'center_x': 0.5, 'top': 0.95}, background_normal='', background_color=(0, 0.75, 1, 1), color=(0.04, 0.06, 0.17, 1))
        self.down_btn = Button(text="v", font_name='assets/fonts/ARCADE_N.TTF', size_hint=btn_sz, pos_hint={'center_x': 0.5, 'y': 0.05}, background_normal='', background_color=(0, 0.75, 1, 1), color=(0.04, 0.06, 0.17, 1))
        self.left_btn = Button(text="<", font_name='assets/fonts/ARCADE_N.TTF', size_hint=btn_sz, pos_hint={'x': 0.20, 'center_y': 0.5}, background_normal='', background_color=(0, 0.75, 1, 1), color=(0.04, 0.06, 0.17, 1))
        self.right_btn = Button(text=">", font_name='assets/fonts/ARCADE_N.TTF', size_hint=btn_sz, pos_hint={'x': 0.65, 'center_y': 0.5}, background_normal='', background_color=(0, 0.75, 1, 1), color=(0.04, 0.06, 0.17, 1))
        self.up_btn.bind(on_release=lambda x: self.process_directional_input('NORTH'))
        self.down_btn.bind(on_release=lambda x: self.process_directional_input('SOUTH'))
        self.left_btn.bind(on_release=lambda x: self.process_directional_input('WEST'))
        self.right_btn.bind(on_release=lambda x: self.process_directional_input('EAST'))
        k_layout.add_widget(self.up_btn)
        k_layout.add_widget(self.down_btn)
        k_layout.add_widget(self.left_btn)
        k_layout.add_widget(self.right_btn)

    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('rotational_maze_high', 1)
        except Exception:
            self.high_score = 1

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['rotational_maze_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def start_game(self, instance):
        self.layout.remove_widget(self.play_help_row)
        self.round_number = 1
        self.score = 0
        self.score_label.text = "SCORE: 0"
        self.hi_score_label.text = f"BEST: ROUND {self.high_score}"
        self.title_label.text = "ROTATIONAL MAZE"
        self.title_label.color = (0, 0.75, 1, 1)
        self.start_round()
        if self.timer_event: Clock.unschedule(self.timer_event)
        self.timer_event = Clock.schedule_interval(self.handle_countdown_tick, 1.0)

    def start_round(self):
        self.time_remaining = 60
        self.timer_label.text = f"TIME: {self.time_remaining}s"
        self.timer_label.color = (0, 0.75, 1, 1)
        self.current_rotation_angle = 0
        self.rotation_instruction.angle = 0
        self.grid_size = 15 + ((self.round_number - 1) // 3) * 2
        if self.grid_size > 25: self.grid_size = 25 
        self.generate_procedural_maze()
        self.game_active = True
        self.draw_maze_shapes()
        if self.rotation_event: Clock.unschedule(self.rotation_event)
        self.rotation_event = Clock.schedule_interval(self.execute_maze_rotation, 3.0)

    def generate_procedural_maze(self):
        self.maze_matrix = [[1 for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        stack = [(1, 1)]
        self.maze_matrix[1][1] = 0
        while stack:
            r, c = stack[-1]
            neighbors = []
            for dr, dc in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                nr, nc = r + dr, c + dc
                if 0 < nr < self.grid_size - 1 and 0 < nc < self.grid_size - 1:
                    if self.maze_matrix[nr][nc] == 1: neighbors.append((nr, nc, dr, dc))
            if neighbors:
                nr, nc, dr, dc = random.choice(neighbors)
                self.maze_matrix[r + dr//2][c + dc//2] = 0
                self.maze_matrix[nr][nc] = 0
                stack.append((nr, nc))
            else: stack.pop()
        self.player_grid_pos = [1, 1]
        self.exit_grid_pos = [self.grid_size - 2, self.grid_size - 2]
        self.maze_matrix[self.player_grid_pos[0]][self.player_grid_pos[1]] = 0
        self.maze_matrix[self.exit_grid_pos[0]][self.exit_grid_pos[1]] = 0

    def execute_maze_rotation(self, dt):
        if not self.game_active: return
        self.current_rotation_angle = (self.current_rotation_angle - 90) % 360
        anim = Animation(angle=self.current_rotation_angle, duration=0.25, t='out_quad')
        anim.start(self.rotation_instruction)

    def process_directional_input(self, compass_command):
        if not self.game_active: return
        dr, dc = 0, 0
        if compass_command == 'NORTH': dr = -1  
        elif compass_command == 'SOUTH': dr = 1   
        elif compass_command == 'WEST': dc = -1  
        elif compass_command == 'EAST': dc = 1   
        new_row = self.player_grid_pos[0] + dr
        new_col = self.player_grid_pos[1] + dc
        if 0 <= new_row < self.grid_size and 0 <= new_col < self.grid_size:
            if self.maze_matrix[new_row][new_col] == 0:
                self.player_grid_pos = [new_row, new_col]
                self.draw_maze_shapes()
                if self.player_grid_pos == self.exit_grid_pos: self.trigger_round_victory()

    def trigger_round_victory(self):
        self.game_active = False
        Clock.unschedule(self.rotation_event)
        self.score += 10
        self.round_number += 1
        self.score_label.text = f"SCORE: {self.score}"
        self.title_label.text = "MAZE EXITED!"
        Clock.schedule_once(lambda dt: self.start_round(), 1.0)

    def draw_maze_shapes(self):
        self.maze_container.canvas.remove_group('maze_shapes')
        cell_size = self.maze_container.width / self.grid_size
        with self.maze_container.canvas:
            for r in range(self.grid_size):
                for c in range(self.grid_size):
                    if self.maze_matrix[r][c] == 1: Color(0.12, 0.16, 0.32, 1, group='maze_shapes') 
                    else: Color(0.04, 0.06, 0.17, 0, group='maze_shapes') 
                    Rectangle(pos=(c * cell_size, (self.grid_size - 1 - r) * cell_size), size=(cell_size, cell_size), group='maze_shapes')
            Color(1, 0.84, 0, 1, group='maze_shapes')
            Rectangle(pos=(self.exit_grid_pos[1] * cell_size, (self.grid_size - 1 - self.exit_grid_pos[0]) * cell_size), size=(cell_size, cell_size), group='maze_shapes')
            Color(0.1, 0.9, 0.2, 1, group='maze_shapes')
            pad = cell_size * 0.20
            Ellipse(pos=(self.player_grid_pos[1] * cell_size + pad, (self.grid_size - 1 - self.player_grid_pos[0]) * cell_size + pad), size=(cell_size - pad*2, cell_size - pad*2), group='maze_shapes')
            Color(0.9, 0.1, 0.1, 1, group='game_shapes')
            mid_c = self.grid_size // 2
            mx = mid_c * cell_size + cell_size / 2
            my = (self.grid_size - 0.4) * cell_size
            Mesh(vertices=[mx, my + cell_size*0.3, 0,0,  mx - cell_size*0.2, my, 0,0,  mx + cell_size*0.2, my, 0,0], indices=[0,1,2], mode='triangles', group='maze_shapes')

    def handle_countdown_tick(self, dt):
        if not self.game_active: return
        self.time_remaining -= 1
        if self.time_remaining > 0:
            self.timer_label.text = f"TIME: {self.time_remaining}s"
            if self.time_remaining <= 10: self.timer_label.color = (0.9, 0.2, 0.2, 1) 
        else: self.stop_game_engine()

    def stop_game_engine(self):
        self.game_active = False
        if self.timer_event: Clock.unschedule(self.timer_event); self.timer_event = None
        if self.rotation_event: Clock.unschedule(self.rotation_event); self.rotation_event = None
        self.maze_container.canvas.remove_group('maze_shapes')
        trigger_haptic_feedback(0.08)
        if self.round_number > self.high_score:
            self.high_score = self.round_number
            self.save_high_score()
            self.title_label.text = "NEW HIGH SCORE!"
            self.title_label.color = (1, 0.84, 0, 1)
        else:
            self.title_label.text = "SYSTEM LOCKDOWN!"
            self.title_label.color = (0, 0.75, 1, 1)
        self.timer_label.text = "TIME: 0s"
        self.hi_score_label.text = f"BEST: ROUND {self.high_score}"
        if self.play_help_row not in self.layout.children:
            self.start_btn.text = "REPLAY MAZE"
            self.play_help_row.disabled = False
            self.layout.add_widget(self.play_help_row)

class SinkyStoneScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.score = 0
        self.high_score = 0
        self.game_active = False
        
        self.player_y = Scale.height_pct(0.5)
        self.player_velocity = 0
        # Inverted Physics scaled via Scale utility
        self.gravity = Scale.vel_h(0.5)            
        self.jump_force = Scale.vel_h(-12.0)       
        self.player_radius = Scale.min_dim(0.04)
        self.player_x = Scale.width_pct(0.25)
        
        self.bubbles = []            
        self.pipes = []              
        self.pipe_width = Scale.min_dim(0.14)
        self.pipe_gap_height = Scale.height_pct(0.26)
        self.game_event = None
        self.load_high_score()

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        with self.canvas.before:
            Color(0.40, 0.75, 0.70, 1) 
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.score_label = Label(
            text="SCORE: 0", font_size=Scale.font(14), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.1, 0.25, 0.25, 1), pos_hint={'center_x': 0.3, 'center_y': 0.85}
        )
        self.layout.add_widget(self.score_label)

        self.hi_score_label = Label(
            text=f"BEST: {self.high_score}", font_size=Scale.font(14), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.1, 0.25, 0.25, 1), pos_hint={'center_x': 0.7, 'center_y': 0.85}
        )
        self.layout.add_widget(self.hi_score_label)

        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='', background_color=(0.75, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        # Action Control Row
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint=(0.9, 0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="DROP STONE", font_size=Scale.font(30), font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 1, 1, 1), size_hint_x=0.8,
            background_normal='', background_color=(0.15, 0.25, 0.25, 1)
        )
        self.start_btn.bind(on_release=self.start_game)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size=Scale.font(16), font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0.15, 0.25, 0.25, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)
        
        self.generate_initial_bubbles()

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Sinky Stone"
        placeholders = [
            "Inverted rules: Gravity pulls your stone UPWARDS",
            "Tap anywhere inside the arena to drive it DOWNWARDS",
            "Thread safely through the gaps inside incoming pipes"
        ]
        overlay = InstructionOverlay(game_name=game_name, rules_list=placeholders, close_callback=self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def on_leave(self, *args):
        self.stop_game_engine()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        # Re-calc relative geometry parameters upon window resize
        self.player_x = Scale.width_pct(0.25)
        self.player_radius = Scale.min_dim(0.04)
        self.pipe_width = Scale.min_dim(0.14)
        self.pipe_gap_height = Scale.height_pct(0.26)
        self.draw_game_elements()

    def go_back_to_menu(self, instance):
        self.stop_game_engine()
        self.clear_board_completely() 
        self.manager.current = 'menu'

    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('sinky_stone_high', 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['sinky_stone_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def generate_initial_bubbles(self):
        self.bubbles = []
        for _ in range(25):
            self.bubbles.append({
                'pos': [random.uniform(0, Window.width), random.uniform(0, Window.height)],
                'size': random.uniform(Scale.font(4), Scale.font(12)), 
                'speed': random.uniform(Scale.vel_w(0.5), Scale.vel_w(2.0))
            })

    def start_game(self, instance):
        self.layout.remove_widget(self.play_help_row)
        self.score = 0
        self.score_label.text = "SCORE: 0"
        self.player_y = Scale.height_pct(0.5)
        self.player_velocity = 0
        self.pipes = []
        self.spawn_pipe()
        self.game_active = True
        if self.game_event: Clock.unschedule(self.game_event)
        self.game_event = Clock.schedule_interval(self.update_game_physics, 1.0 / 60.0)

    def spawn_pipe(self):
        gap_y = random.uniform(Scale.height_pct(0.20), Scale.height_pct(0.65))
        self.pipes.append({'x': Window.width + dp(20), 'gap_y': gap_y, 'gap_h': self.pipe_gap_height, 'passed': False})

    def on_touch_down(self, touch):
        if self.back_btn.collide_point(*touch.pos): return super().on_touch_down(touch)
        if self.game_active:
            self.player_velocity = self.jump_force
            return True
        return super().on_touch_down(touch)

    def update_game_physics(self, dt):
        if not self.game_active: return
        
        for b in self.bubbles:
            b['pos'][0] -= b['speed'] * (dt * 60.0)
            if b['pos'][0] < -b['size']:
                b['pos'][0] = Window.width + b['size']
                b['pos'][1] = random.uniform(0, Window.height)
                
        self.player_velocity += self.gravity * (dt * 60.0)
        self.player_y += self.player_velocity * (dt * 60.0)
        
        if self.player_y >= Window.height or self.player_y <= 0:
            self.trigger_game_over()
            trigger_haptic_feedback(0.08)
            return
            
        pipes_to_remove = []
        spawn_new = False
        scroll_speed = Scale.vel_w(3.0) * (dt * 60.0)
        
        for p in self.pipes:
            p['x'] -= scroll_speed
            if len(self.pipes) == 1 and p['x'] < Window.width * 0.45: 
                spawn_new = True
            if p['x'] < -self.pipe_width: 
                pipes_to_remove.append(p)
                
            if not p['passed'] and p['x'] + self.pipe_width < self.player_x:
                p['passed'] = True
                self.score += 1
                self.score_label.text = f"SCORE: {self.score}"
                if self.score > self.high_score:
                    self.high_score = self.score
                    self.hi_score_label.text = f"BEST: {self.high_score}"
                    self.save_high_score()
                    
            r = self.player_radius
            stone_left, stone_right = self.player_x - r + dp(2), self.player_x + r - dp(2)
            stone_bottom, stone_top = self.player_y - r + dp(2), self.player_y + r - dp(2)
            pipe_left, pipe_right = p['x'], p['x'] + self.pipe_width
            
            if pipe_left < stone_right and pipe_right > stone_left:
                if stone_top > (p['gap_y'] + p['gap_h']) or stone_bottom < p['gap_y']:
                    self.trigger_game_over()
                    trigger_haptic_feedback(0.08)
                    return
                    
        if spawn_new: 
            self.spawn_pipe()
        for r_p in pipes_to_remove: 
            self.pipes.remove(r_p)
            
        self.draw_game_elements()

    def draw_game_elements(self):
        self.canvas.before.remove_group('sinky_shapes')
        with self.canvas.before:
            for b in self.bubbles:
                Color(0.55, 0.88, 0.82, 0.45, group='sinky_shapes') 
                Ellipse(pos=(b['pos'][0], b['pos'][1]), size=(b['size'], b['size']), group='sinky_shapes')
            Color(0.20, 0.24, 0.26, 1, group='sinky_shapes')
            for p in self.pipes:
                Rectangle(pos=(p['x'], 0), size=(self.pipe_width, p['gap_y']), group='sinky_shapes')
                top_p_h = Window.height - (p['gap_y'] + p['gap_h'])
                Rectangle(pos=(p['x'], p['gap_y'] + p['gap_h']), size=(self.pipe_width, top_p_h), group='sinky_shapes')
            if self.game_active or self.play_help_row not in self.layout.children:
                Color(0.78, 0.80, 0.82, 1, group='sinky_shapes')
                r = self.player_radius
                Rectangle(pos=(self.player_x - r, self.player_y - r), size=(r*2, r*2), group='sinky_shapes')

    def trigger_game_over(self):
        self.stop_game_engine()
        if self.play_help_row not in self.layout.children:
            self.start_btn.text = "RETRY DROP"
            self.play_help_row.disabled = False
            self.layout.add_widget(self.play_help_row)

    def clear_board_completely(self):
        self.pipes = []
        self.player_y = Scale.height_pct(0.5)
        self.player_velocity = 0
        self.canvas.before.remove_group('sinky_shapes')

    def stop_game_engine(self):
        self.game_active = False
        if self.game_event: Clock.unschedule(self.game_event); self.game_event = None

class GridLockScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.round_number = 1
        self.score = 0               
        self.high_score = 0
        self.time_remaining = 90    
        self.game_active = False
        self.cols_count = 7
        self.rows_count = 7
        self.grid_matrix = {}        
        self.playing_card = None     
        self.colors = [(0.9, 0.2, 0.2, 1), (0.1, 0.7, 0.3, 1), (0, 0.6, 0.9, 1), (0.9, 0.7, 0, 1), (0.6, 0.2, 0.8, 1)]
        self.shapes = ['SQUARE', 'TRIANGLE', 'CIRCLE', 'DIAMOND', 'CROSS']
        self.timer_event = None
        self.grid_lines_group = None

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.title_label = Label(
            text="GRID LOCK", font_size=Scale.font(30), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.96}
        )
        self.layout.add_widget(self.title_label)

        self.timer_label = Label(
            text="TIME: 90s", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.93}
        )
        self.layout.add_widget(self.timer_label)

        self.score_label = Label(
            text="SCORE: 0", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.35, 'center_y': 0.87}
        )
        self.layout.add_widget(self.score_label)

        self.load_high_score()
        self.hi_score_label = Label(
            text=f"BEST: {self.high_score}", font_size='10sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.7, 'center_y': 0.87}
        )
        self.layout.add_widget(self.hi_score_label)

        self.status_label = Label(
            text="BORDER=SHAPE | NO BORDER=COLOR", font_size='8sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.84}
        )
        self.layout.add_widget(self.status_label)

        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1}
        )
        self.back_btn.background_normal = ''
        self.back_btn.background_color = (0.8, 0.25, 0.25, 1)
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        self.deck_wrapper = RelativeLayout(size_hint=(None, None), size=(Window.width * 0.11, Window.width * 0.11), pos_hint={'center_x': 0.5, 'center_y': 0.75})
        self.layout.add_widget(self.deck_wrapper)

        self.grid_container = RelativeLayout(size_hint=(0.88, 0.44), pos_hint={'center_x': 0.5, 'center_y': 0.42})
        self.layout.add_widget(self.grid_container)
        
        with self.grid_container.canvas.before:
            Color(0, 0.75, 1, 1)
            self.grid_lines_group = InstructionGroup()
            self.grid_container.canvas.before.add(self.grid_lines_group)

        self.bin_btn = Button(
            text="[BIN]", font_size='10sp', font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.18, 0.06), pos_hint={'right': 0.94, 'y': 0.10}
        )
        self.bin_btn.background_normal = ''
        self.bin_btn.background_color = (0.5, 0.5, 0.5, 1)
        self.bin_btn.bind(on_release=self.flush_playing_card)
        self.layout.add_widget(self.bin_btn)

        # 🟢 ROW WRAPPER
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint=(0.9,0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.25}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), size_hint_x=0.8
        )
        self.start_btn.background_normal = ''
        self.start_btn.background_color = (0, 0.75, 1, 1)
        self.start_btn.bind(on_release=self.start_game)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size='14sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)
        
    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Grid Lock"
        placeholders = [
            "If incoming cards have a border: Match by interior SHAPE profile",
            "If incoming cards lack a border: Match by background color profile",
            "Clear entire blocks to prevent grid locking terminal states",
            "If you cannot find a valid tile to clear, bin your card to get a new one"
        ]
        overlay = InstructionOverlay(game_name=game_name, rules_list=placeholders, close_callback=self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def on_leave(self, *args):
        self.stop_game_engine()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('grid_lock_high', 0)
        except Exception:
            self.high_score = 0
            
    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['grid_lock_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def go_back_to_menu(self, instance):
        self.stop_game_engine()
        self.manager.current = 'menu'

    def start_game(self, instance):
        self.layout.remove_widget(self.play_help_row)
        self.round_number = 1
        self.score = 0                 
        self.score_label.text = "SCORE: 0"
        self.cols_count = 7
        self.rows_count = 7
        self.start_round()
        if self.timer_event: Clock.unschedule(self.timer_event)
        self.timer_event = Clock.schedule_interval(self.handle_clock_tick, 1.0)

    def start_round(self):
        self.time_remaining = 90       
        self.timer_label.text = f"TIME: {self.time_remaining}s"
        self.score_label.text = f"SCORE: {self.score}" 
        if self.round_number > 1:
            if self.round_number % 2 == 0: self.rows_count += 1
            else: self.cols_count += 1
        self.grid_container.clear_widgets()
        self.grid_lines_group.clear()
        self.grid_matrix = {}
        self.matrix_grid = GridLayout(cols=self.cols_count, rows=self.rows_count, spacing=dp(3), size_hint=(1, 1))
        self.grid_container.add_widget(self.matrix_grid)
        for r in range(self.rows_count):
            for c in range(self.cols_count):
                tile = Button(background_normal='', background_color=(0,0,0,0))
                tile.grid_coords = (r, c)
                tile.bind(on_release=self.handle_grid_placement)
                tile.bind(size=self.refresh_single_tile_render, pos=self.refresh_single_tile_render)
                self.matrix_grid.add_widget(tile)
                is_inner = (0 < r < self.rows_count - 1) and (0 < c < self.cols_count - 1)
                if is_inner:
                    self.grid_matrix[(r, c)] = {
                        'color': random.choice(self.colors), 'type': random.choice(self.shapes),
                        'locked': False, 'empty': False, 'widget': tile
                    }
                else:
                    self.grid_matrix[(r, c)] = {
                        'color': (0,0,0,0), 'type': None, 'locked': False, 'empty': True, 'widget': tile
                    }
        self.game_active = True
        Clock.schedule_once(self.draw_wireframe_lines, 0.1)
        self.roll_next_playing_card()

    def draw_wireframe_lines(self, dt):
        if not self.matrix_grid: return
        self.grid_lines_group.clear()
        for coord, data in self.grid_matrix.items():
            abs_pos = self.matrix_grid.to_parent(data['widget'].x, data['widget'].y, relative=True)
            self.grid_lines_group.add(Line(rectangle=(abs_pos[0], abs_pos[1], data['widget'].width, data['widget'].height), width=dp(1)))

    def roll_next_playing_card(self):
        active_cards = [data for data in self.grid_matrix.values() if not data['empty'] and not data['locked']]
        if not active_cards:
            self.trigger_round_victory()
            return
        donor = random.choice(active_cards)
        has_border = random.choice([True, False])
        self.playing_card = {
            'color': random.choice(self.colors) if has_border else donor['color'],
            'type': donor['type'] if has_border else random.choice(self.shapes), 'border': has_border
        }
        self.render_deck_queue_slot()

    def render_deck_queue_slot(self):
        self.deck_wrapper.canvas.clear()
        if not self.playing_card: return
        w, h = self.deck_wrapper.width, self.deck_wrapper.height
        with self.deck_wrapper.canvas:
            Color(*self.playing_card['color'])
            Rectangle(pos=(0, 0), size=(w, h))
            if self.playing_card['border']:
                Color(1, 1, 1, 1) 
                Line(rectangle=(1, 1, w - 2, h - 2), width=dp(2))
            Color(0, 0, 0, 1)
            self.draw_vector_shape_geometry(self.playing_card['type'], w/2, h/2, w * 0.45)

    def draw_vector_shape_geometry(self, stype, cx, cy, sz):
        if stype == 'SQUARE': Rectangle(pos=(cx - sz/2, cy - sz/2), size=(sz, sz))
        elif stype == 'TRIANGLE': Mesh(vertices=[cx, cy + sz/2, 0,0,  cx - sz/2, cy - sz/2, 0,0,  cx + sz/2, cy - sz/2, 0,0], indices=[0,1,2], mode='triangles')
        elif stype == 'CIRCLE': Ellipse(pos=(cx - sz/2, cy - sz/2), size=(sz, sz))
        elif stype == 'DIAMOND': Mesh(vertices=[cx, cy + sz/2, 0,0,  cx - sz/2, cy, 0,0,  cx, cy - sz/2, 0,0,  cx + sz/2, cy, 0,0], indices=[0,1,2, 0,2,3], mode='triangles')
        elif stype == 'CROSS':
            Rectangle(pos=(cx - sz/6, cy - sz/2), size=(sz/3, sz))
            Rectangle(pos=(cx - sz/2, cy - sz/6), size=(sz, sz/3))

    def handle_grid_placement(self, instance):
        if not self.game_active or not self.playing_card: return
        r, c = instance.grid_coords
        node = self.grid_matrix[(r, c)]
        if not node['empty'] or node['locked']: return
        matched_neighbors = []
        for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
            nr, nc = r + dr, c + dc
            if (nr, nc) in self.grid_matrix:
                neigh = self.grid_matrix[(nr, nc)]
                if not neigh['empty'] and not neigh['locked']:
                    if self.playing_card['border']:
                        if neigh['type'] == self.playing_card['type']: matched_neighbors.append((nr, nc))
                    else:
                        if neigh['color'] == self.playing_card['color']: matched_neighbors.append((nr, nc))
        if matched_neighbors:
            for nr, nc in matched_neighbors:
                self.grid_matrix[(nr, nc)]['empty'] = True
                self.grid_matrix[(nr, nc)]['color'] = (0,0,0,0)
                self.grid_matrix[(nr, nc)]['type'] = None
                self.refresh_single_tile_render(self.grid_matrix[(nr, nc)]['widget'])
            self.grid_matrix[(r, c)]['empty'] = True
            self.refresh_single_tile_render(instance)
            self.score += 1
            self.score_label.text = f"SCORE: {self.score}"
            if self.score > self.high_score:
                self.high_score = self.score
                self.hi_score_label.text = f"BEST: {self.high_score}"
                self.save_high_score()
            self.roll_next_playing_card()
        else:
            trigger_haptic_feedback(0.08)
            node['locked'] = True
            self.refresh_single_tile_render(instance)
            if self.check_for_total_gridlock():
                self.stop_game_engine()
                return
            self.roll_next_playing_card()
            
    def check_for_total_gridlock(self):
        for coord, data in self.grid_matrix.items():
            if data['empty'] and not data['locked']: return False 
        return True 

    def flush_playing_card(self, instance):
        if self.game_active: self.roll_next_playing_card()

    def refresh_single_tile_render(self, instance, *args):
        instance.canvas.clear()
        coords = instance.grid_coords
        if coords not in self.grid_matrix: return
        data = self.grid_matrix[coords]
        with instance.canvas:
            if data['locked']:
                Color(0.8, 0.15, 0.15, 1) 
                Rectangle(pos=instance.pos, size=instance.size)
            elif data['empty']:
                Color(0, 0, 0, 0) 
                Rectangle(pos=instance.pos, size=instance.size)
            else:
                Color(*data['color'])
                Rectangle(pos=instance.pos, size=instance.size)
                Color(0, 0, 0, 1) 
                self.draw_vector_shape_geometry(data['type'], instance.x + instance.width/2, instance.y + instance.height/2, instance.width * 0.45)

    def trigger_round_victory(self):
        self.game_active = False
        self.title_label.text = "BOARD CLEARED!"
        self.round_number += 1
        Clock.schedule_once(lambda dt: self.start_round(), 1.2)

    def handle_clock_tick(self, dt):
        if not self.game_active: return
        self.time_remaining -= 1
        if self.time_remaining > 0: self.timer_label.text = f"TIME: {self.time_remaining}s"
        else: self.stop_game_engine()

    def stop_game_engine(self):
        self.game_active = False
        if self.timer_event: Clock.unschedule(self.timer_event); self.timer_event = None
        self.grid_container.clear_widgets()
        if self.grid_lines_group: self.grid_lines_group.clear()
        self.deck_wrapper.canvas.clear()
        self.title_label.text = "GAME OVER"
        if self.play_help_row not in self.layout.children:
            self.start_btn.text = "REPLAY GRID"
            self.play_help_row.disabled = False
            self.layout.add_widget(self.play_help_row)

class AgainstGrainScreen(Screen):
    def __init__(self, **kwargs):
        super(AgainstGrainScreen, self).__init__(**kwargs)
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        
        # Game State Variables
        self.game_active = False
        self.score = 0
        self.high_score = 0
        self.time_remaining = 60
        self.grid_triangles = []
        self.majority_dir = 'UP'
        self.odd_dir = 'UP'
        self.odd_slot_idx = 0
        self.correct_swipe = 'UP'
        
        # Input/Timer Handles
        self.touch_start_pos = None
        self.timer_event = None
        self.flash_timer = 0.0
        
        # System Deep Background Canvas Layer (#0A0F2C)
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        
        # Build Standardized Retro UI Elements
        self.title_label = Label(
            text="AGAINST THE GRAIN", font_size='16sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.9}
        )
        self.layout.add_widget(self.title_label)
        
        self.timer_label = Label(
            text="TIME: 60s", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.8}
        )
        self.layout.add_widget(self.timer_label)
        
        self.score_label = Label(
            text="SCORE: 0", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.3, 'center_y': 0.85}
        )
        self.layout.add_widget(self.score_label)

        self.load_high_score()
        self.hi_score_label = Label(
            text=f"BEST: {self.high_score}", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.7, 'center_y': 0.85}
        )
        self.layout.add_widget(self.hi_score_label)
        
        # Standard Pinned Top-Left Back Button Configuration
        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)
        
        # 🟢 ROW WRAPPER REPLACEMENT
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint=(0.9,0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), size_hint_x=0.8,
            background_normal='', background_color=(0, 0.75, 1, 1)
        )
        self.start_btn.bind(on_release=lambda x: self.start_game())
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size='16sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Against Grain"
        placeholders = [
            "Spot the lone triangle facing in another direction",
            "Swipe in the direction of the rogue triangle",
            "If all triangles are pointing in the same direction, swipe in that direction"
        ]
        overlay = InstructionOverlay(game_name=game_name, rules_list=placeholders, close_callback=self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def on_pre_enter(self):
        self.stop_game_engine()
        self.title_label.text = "AGAINST THE GRAIN"
        self.title_label.color = (0, 0.75, 1, 1)
        self.timer_label.text = "TIME: 60s"
        self.load_high_score()
        self.score_label.text = "SCORE: 0"
        self.hi_score_label.text = f"BEST: {self.high_score}"
        if self.play_help_row not in self.layout.children:
            self.layout.add_widget(self.play_help_row)
        self.play_help_row.disabled = False

    def on_leave(self):
        self.stop_game_engine()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def go_back_to_menu(self, instance):
        self.manager.current = 'menu'

    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('against_grain_high', 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['against_grain_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def start_game(self):
        if self.play_help_row in self.layout.children:
            self.layout.remove_widget(self.play_help_row)
            
        self.game_active = True
        self.score = 0
        self.time_remaining = 60
        self.score_label.text = f"SCORE: {self.score}"
        self.timer_label.text = f"TIME: {self.time_remaining}s"
        self.title_label.text = "SWIPE ODD ONE OUT!"
        self.title_label.color = (0, 0.75, 1, 1)
        
        self.roll_global_rule_state()
        self.draw_against_grain_canvas()
        
        if self.timer_event:
            Clock.unschedule(self.timer_event)
        self.timer_event = Clock.schedule_interval(self.game_loop_tick, 0.016)

    def stop_game_engine(self):
        self.game_active = False
        if self.timer_event:
            Clock.unschedule(self.timer_event)
            self.timer_event = None
            
        self.canvas.remove_group('grain_shapes')
        self.timer_label.color = (0, 0.75, 1, 1)
        self.score_label.color = (0, 0.75, 1, 1)
        self.hi_score_label.color = (0, 0.75, 1, 1)
        
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
            self.title_label.text = "NEW HIGH SCORE!"
            self.title_label.color = (1, 0.84, 0, 1)
        else:
            self.title_label.text = "SHIFT OVER"
            self.title_label.color = (0, 0.75, 1, 1)
            
        #self.timer_label.text = f"FINAL SCORE: {self.score}"
        self.hi_score_label.text = f"BEST: {self.high_score}"
        
        if self.play_help_row not in self.layout.children:
            self.start_btn.text = "PLAY AGAIN"
            self.play_help_row.disabled = False
            self.layout.add_widget(self.play_help_row)

    def game_loop_tick(self, dt):
        if not self.game_active:
            return
            
        if self.flash_timer > 0:
            self.flash_timer -= dt
            if self.flash_timer <= 0:
                self.timer_label.color = (0, 0.75, 1, 1)
                self.score_label.color = (0, 0.75, 1, 1)
                self.hi_score_label.color = (0, 0.75, 1, 1)

        self.time_remaining = round(max(0.0, self.time_remaining - dt), 2)
        self.timer_label.text = f"TIME: {int(self.time_remaining)}s"
        
        if self.time_remaining <= 0:
            self.stop_game_engine()

    def roll_global_rule_state(self):
        directions = ['UP', 'DOWN', 'LEFT', 'RIGHT']
        self.majority_dir = random.choice(directions)
        self.odd_slot_idx = random.randint(0, 8)
        self.odd_dir = random.choice(directions)
        
        if self.odd_dir == self.majority_dir:
            self.correct_swipe = self.majority_dir
        else:
            self.correct_swipe = self.odd_dir
            
        self.build_grid_matrix()

    def build_grid_matrix(self):
        self.grid_triangles = []
        cx, cy = Window.width / 2, Window.height * 0.44
        spacing = Window.width * 0.18 
        
        idx = 0
        for row in [-1, 0, 1]:
            for col in [-1, 0, 1]:
                slot_x = cx + (col * spacing)
                slot_y = cy + (row * spacing)
                
                current_dir = self.odd_dir if idx == self.odd_slot_idx else self.majority_dir
                
                self.grid_triangles.append({
                    'cx': slot_x,
                    'cy': slot_y,
                    'dir': current_dir
                })
                idx += 1

    def draw_against_grain_canvas(self):
        self.canvas.remove_group('grain_shapes')
        if not self.game_active:
            return
            
        with self.canvas:
            shape_sz = Window.width * 0.050
            for t in self.grid_triangles:
                Color(1, 1, 1, 1, group='grain_shapes')
                self.draw_vector_shape_geometry(t['cx'], t['cy'], shape_sz, orientation=t['dir'], group='grain_shapes')

    def draw_vector_shape_geometry(self, cx, cy, size, orientation='UP', group=''):
        if orientation == 'UP':
            v = [cx, cy + size, 0, 0, cx - size, cy - size, 0, 0, cx + size, cy - size, 0, 0]
        elif orientation == 'DOWN':
            v = [cx, cy - size, 0, 0, cx - size, cy + size, 0, 0, cx + size, cy + size, 0, 0]
        elif orientation == 'LEFT':
            v = [cx - size, cy, 0, 0, cx + size, cy + size, 0, 0, cx + size, cy - size, 0, 0]
        else:  # RIGHT
            v = [cx + size, cy, 0, 0, cx - size, cy + size, 0, 0, cx - size, cy - size, 0, 0]
            
        Mesh(vertices=v, indices=[0, 1, 2], mode='triangles', group=group)

    def on_touch_down(self, touch):
        if self.back_btn.collide_point(*touch.pos):
            return super(AgainstGrainScreen, self).on_touch_down(touch)
        if not self.game_active:
            return super(AgainstGrainScreen, self).on_touch_down(touch)
        self.touch_start_pos = touch.pos
        return True

    def on_touch_up(self, touch):
        if self.back_btn.collide_point(*touch.pos):
            return super(AgainstGrainScreen, self).on_touch_up(touch)
        if not self.game_active or not self.touch_start_pos:
            return super(AgainstGrainScreen, self).on_touch_up(touch)
            
        dx = touch.x - self.touch_start_pos[0]
        dy = touch.y - self.touch_start_pos[1]
        self.touch_start_pos = None
        
        if math.sqrt(dx*dx + dy*dy) < dp(20):
            return True
            
        if abs(dx) > abs(dy):
            swipe_dir = 'RIGHT' if dx > 0 else 'LEFT'
        else:
            swipe_dir = 'UP' if dy > 0 else 'DOWN'
            
        self.evaluate_swipe_input(swipe_dir)
        return True

    def evaluate_swipe_input(self, user_swipe_direction):
        if user_swipe_direction == self.correct_swipe:
            self.score += 1
            self.score_label.text = f"SCORE: {self.score}"
            self.roll_global_rule_state()
            self.draw_against_grain_canvas()
        else:
            trigger_haptic_feedback(0.08)
            self.time_remaining = max(0.0, self.time_remaining - 2.0)
            self.timer_label.text = f"TIME: {int(self.time_remaining)}s"
            
            self.timer_label.color = (0.9, 0.2, 0.2, 1)
            self.score_label.color = (0.9, 0.2, 0.2, 1)
            self.hi_score_label.color = (0.9, 0.2, 0.2, 1)
            self.flash_timer = 0.35
            
            self.roll_global_rule_state()
            self.draw_against_grain_canvas()

class HigherEquationScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.score = 0
        self.high_score = 0
        self.time_remaining = 60
        self.game_active = False
        self.eq1_text = ""
        self.eq1_val = 0
        self.eq2_text = ""
        self.eq2_val = 0
        self.timer_event = None
        self.flash_red_btn = None
        self.flash_timer = 0.0
        
        self.load_high_score()

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.title_label = Label(
            text="HIGHER EQUATION", font_size='18sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.9}
        )
        self.layout.add_widget(self.title_label)

        self.timer_label = Label(
            text="TIME: 60s", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.75}
        )
        self.layout.add_widget(self.timer_label)

        self.score_label = Label(
            text="SCORE: 0", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.3, 'center_y': 0.8}
        )
        self.layout.add_widget(self.score_label)

        self.hi_score_label = Label(
            text=f"BEST: {self.high_score}", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.7, 'center_y': 0.8}
        )
        self.layout.add_widget(self.hi_score_label)

        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        self.top_btn = Button(
            text="", font_size='18sp', font_name='assets/fonts/ARCADE_N.TTF', color=(0.04, 0.06, 0.17, 1),
            size_hint=(0.75, 0.14), pos_hint={'center_x': 0.5, 'center_y': 0.52},
            background_normal='', background_color=(1, 1, 1, 1)
        )
        self.top_btn.bind(on_release=lambda x: self.evaluate_choice(self.top_btn, self.eq1_val, self.eq2_val))

        self.bottom_btn = Button(
            text="", font_size='18sp', font_name='assets/fonts/ARCADE_N.TTF', color=(0.04, 0.06, 0.17, 1),
            size_hint=(0.75, 0.14), pos_hint={'center_x': 0.5, 'center_y': 0.34},
            background_normal='', background_color=(1, 1, 1, 1)
        )
        self.bottom_btn.bind(on_release=lambda x: self.evaluate_choice(self.bottom_btn, self.eq2_val, self.eq1_val))

        # 🟢 ROW WRAPPER
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint=(0.9,0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), size_hint_x=0.8,
            background_normal='', background_color=(0, 0.75, 1, 1)
        )
        self.start_btn.bind(on_release=self.trigger_countdown)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size='16sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Higher Equation"
        placeholders = [
            "Compute both mathematical expressions presented inside cards",
            "Evaluate variables quickly and tap the card yielding the highest sum",
            "Wrong calculations deploy a 1 second penalty block loop"
        ]
        overlay = InstructionOverlay(game_name=game_name, rules_list=placeholders, close_callback=self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def on_leave(self, *args):
        self.stop_game_engine()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def go_back_to_menu(self, instance):
        self.stop_game_engine()
        self.manager.current = 'menu'

    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('higher_equation_high', 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['higher_equation_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def trigger_countdown(self, instance):
        self.layout.remove_widget(self.play_help_row)
        self.score = 0
        self.time_remaining = 60
        self.score_label.text = "SCORE: 0"
        self.timer_label.text = "TIME: 60s"
        self.hi_score_label.text = f"BEST: {self.high_score}"
        self.title_label.text = "HIGHER EQUATION"
        self.title_label.color = (0, 0.75, 1, 1)
        self.countdown_ticks = 3
        self.title_label.text = f"GET READY: {self.countdown_ticks}"
        Clock.schedule_interval(self.handle_countdown_tick, 1.0)

    def handle_countdown_tick(self, dt):
        self.countdown_ticks -= 1
        if self.countdown_ticks > 0: self.title_label.text = f"GET READY: {self.countdown_ticks}"
        else:
            Clock.unschedule(self.handle_countdown_tick)
            self.title_label.text = "TAP THE HIGHER VAL!"
            self.start_game_loop()

    def start_game_loop(self):
        self.game_active = True
        self.top_btn.background_color = (1, 1, 1, 1)
        self.bottom_btn.background_color = (1, 1, 1, 1)
        if self.top_btn not in self.layout.children: self.layout.add_widget(self.top_btn)
        if self.bottom_btn not in self.layout.children: self.layout.add_widget(self.bottom_btn)
        self.generate_smart_challenges()
        self.timer_event = Clock.schedule_interval(self.handle_clock_tick, 1.0)

    def generate_smart_challenges(self):
        mode = random.choice(['STATIC', 'STRUCTURAL'])
        ops = ['+', '-', 'x']
        op = random.choice(ops)
        if mode == 'STATIC':
            base_val = random.randint(20, 80) if op != 'x' else random.randint(12, 50)
            variance = random.choice([-5, -4, -3, -2, -1, 1, 2, 3, 4, 5])
            target_val = base_val + variance
            eq_text = ""
            if op == '+':
                a = random.randint(5, base_val - 5)
                eq_text = f"{a} + {base_val - a}"
            elif op == '-':
                b = random.randint(5, 25)
                eq_text = f"{base_val + b} - {b}"
            else:
                factors = [i for i in range(2, 11) if base_val % i == 0]
                a = random.choice(factors) if factors else 5
                b = base_val // a if factors else 5
                eq_text = f"{a} x {b}"
                base_val = a * b
            if random.choice([True, False]):
                self.eq1_text, self.eq1_val = eq_text, base_val
                self.eq2_text, self.eq2_val = str(target_val), target_val
            else:
                self.eq1_text, self.eq1_val = str(target_val), target_val
                self.eq2_text, self.eq2_val = eq_text, base_val
        else:
            common = random.randint(15, 50) if op != 'x' else random.randint(4, 9)
            v1 = random.randint(5, 25) if op != 'x' else random.randint(3, 9)
            v2 = v1 + random.choice([-4, -3, -2, -1, 1, 2, 3, 4])
            if v2 < 1: v2 = v1 + 2
            if op == '+':
                self.eq1_text, self.eq1_val = f"{common} + {v1}", common + v1
                self.eq2_text, self.eq2_val = f"{common} + {v2}", common + v2
            elif op == '-':
                self.eq1_text, self.eq1_val = f"{common} - {v1}", common - v1
                self.eq2_text, self.eq2_val = f"{common} - {v2}", common - v2
            else:
                self.eq1_text, self.eq1_val = f"{common} x {v1}", common * v1
                self.eq2_text, self.eq2_val = f"{common} x {v2}", common * v2
            if random.choice([True, False]):
                self.eq1_text, self.eq2_text = self.eq2_text, self.eq1_text
                self.eq1_val, self.eq2_val = self.eq2_val, self.eq1_val
        self.top_btn.text = self.eq1_text
        self.bottom_btn.text = self.eq2_text

    def evaluate_choice(self, clicked_widget, chosen_val, comparison_val):
        if not self.game_active or self.flash_timer > 0: return
        if chosen_val > comparison_val:
            self.score += 1
            self.score_label.text = f"SCORE: {self.score}"
            self.generate_smart_challenges()
        else:
            trigger_haptic_feedback(0.08)
            self.time_remaining = max(0, self.time_remaining - 1)
            self.timer_label.text = f"TIME: {self.time_remaining}s"
            self.timer_label.color = (0.9, 0.2, 0.2, 1)
            self.flash_red_btn = clicked_widget
            self.flash_red_btn.background_color = (0.8, 0.15, 0.15, 1) 
            self.flash_timer = 0.35
            Clock.schedule_once(self.clear_red_flash, 0.35)

    def clear_red_flash(self, dt):
        if self.flash_red_btn: self.flash_red_btn.background_color = (1, 1, 1, 1)
        self.flash_timer = 0.0
        self.generate_smart_challenges()

    def handle_clock_tick(self, dt):
        self.time_remaining -= 1
        if self.time_remaining > 0:
            self.timer_label.text = f"TIME: {self.time_remaining}s"
            if self.time_remaining > 10: self.timer_label.color = (0, 0.75, 1, 1)
        else: self.stop_game_engine()

    def stop_game_engine(self):
        self.game_active = False
        if self.timer_event: Clock.unschedule(self.timer_event); self.timer_event = None
        if self.top_btn in self.layout.children: self.layout.remove_widget(self.top_btn)
        if self.bottom_btn in self.layout.children: self.layout.remove_widget(self.bottom_btn)
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
            self.title_label.text = "NEW HIGH SCORE!"
            self.title_label.color = (1, 0.84, 0, 1) 
        else:
            self.title_label.text = "TIME UP!"
            self.title_label.color = (0, 0.75, 1, 1)
        #self.timer_label.text = f"FINAL SCORE: {self.score}"
        self.hi_score_label.text = f"BEST: {self.high_score}"
        if self.play_help_row not in self.layout.children:
            self.start_btn.text = "PLAY AGAIN"
            self.play_help_row.disabled = False
            self.layout.add_widget(self.play_help_row)

class WhatsNextScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.correct_choices = 0
        self.game_active = False
        self.colors = [(0.9, 0.2, 0.2, 1), (0.1, 0.7, 0.3, 1), (0, 0.6, 0.9, 1), (0.9, 0.7, 0, 1), (0.6, 0.2, 0.8, 1)]
        self.shapes = ['SQUARE', 'TRIANGLE', 'CIRCLE', 'DIAMOND', 'CROSS']
        self.rule_types = ['MIN_SHAPES', 'MAX_SHAPES', 'CENTER_OCCUPIED', 'UNIQUE_SHAPE', 'UNIQUE_COLOR', 'EVEN_SHAPES', 'ODD_SHAPES', 'DIAGONAL_LINE']
        self.current_secret_rule = None
        self.history_rows = []        
        self.current_correct_idx = -1 
        self.row_counter = 0
        self.timer_event = None
        self.status_reveal_bg = None

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.title_label = Label(
            text="WHATS NEXT?", font_size='16sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.95}
        )
        self.layout.add_widget(self.title_label)

        self.score_label = Label(
            text="PROGRESS: 0/5", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.90}
        )
        self.layout.add_widget(self.score_label)
        
        self.status_label = Label(
            text="WATCH FOR THE SECRET CONSTRAINTS", font_size='8sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.85}
        )
        self.layout.add_widget(self.status_label)

        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        self.scroll_view = ScrollView(size_hint=(0.95, 0.70), pos_hint={'center_x': 0.5, 'top': 0.83}, do_scroll_x=False, do_scroll_y=True)
        self.layout.add_widget(self.scroll_view)
        
        self.rows_container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(10), padding=[0, dp(10), 0, dp(10)])
        self.rows_container.bind(minimum_height=self.rows_container.setter('height'))
        self.scroll_view.add_widget(self.rows_container)

        # 🟢 ROW WRAPPER
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint=(0.9,0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), size_hint_x=0.8,
            background_normal='', background_color=(0, 0.75, 1, 1)
        )
        self.start_btn.bind(on_release=self.start_game)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size='16sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Whats Next"
        placeholders = [
            "Analyze successive rows to deduce the secret logic rules",
            "Select the specific card that satisfies conditions",
            "Reach 5 correct patterns to completely decrypt the riddle"
        ]
        overlay = InstructionOverlay(game_name=game_name, rules_list=placeholders, close_callback=self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def go_back_to_menu(self, instance):
        self.stop_game_engine()
        self.manager.current = 'menu'

    def start_game(self, instance):
        self.layout.remove_widget(self.play_help_row)
        self.correct_choices = 0
        self.row_counter = 0
        self.score_label.text = "PROGRESS: 0/5"
        self.rows_container.clear_widgets()
        self.history_rows = []
        self.status_label.canvas.before.clear()
        self.status_reveal_bg = None
        self.current_secret_rule = random.choice(self.rule_types)
        self.title_label.text = "WHATS NEXT?"
        self.status_label.text = "WATCH FOR THE SECRET CONSTRAINTS"
        self.status_label.color = (0, 0.75, 1, 1)
        self.game_active = True
        self.spawn_new_puzzle_row()
        self.spawn_new_puzzle_row()

    def spawn_new_puzzle_row(self):
        if not self.game_active: return
        self.row_counter += 1
        sq_data = self.generate_row_data_by_rule()
        row_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=Window.width * 0.24, spacing=dp(6))
        row_num_lbl = Label(text=f"#{self.row_counter:02d}", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF', color=(0, 0.5, 0.8, 1), size_hint=(0.14, 1))
        row_layout.add_widget(row_num_lbl)
        row_buttons = []
        for i in range(3):
            btn = Button(background_normal='', background_color=(1, 1, 1, 1), size_hint=(0.28, 1))
            btn.row_index = self.row_counter
            btn.sq_index = i
            btn.sq_profile = sq_data[i]
            btn.bind(on_release=self.handle_square_selection)
            btn.bind(size=self.render_matrix_grid, pos=self.render_matrix_grid)
            row_layout.add_widget(btn)
            row_buttons.append(btn)
        self.rows_container.add_widget(row_layout, index=len(self.rows_container.children))
        self.history_rows.append({'layout': row_layout, 'buttons': row_buttons, 'resolved': False, 'correct_idx': self.current_correct_idx})
        Clock.schedule_once(lambda dt: setattr(self.scroll_view, 'scroll_y', 1.0), 0.1)

    def generate_row_data_by_rule(self):
        profiles = [{'color': random.choice(self.colors), 'shape': random.choice(self.shapes), 'matrix': []} for _ in range(3)]
        self.current_correct_idx = random.randint(0, 2)
        wrong_indices = [idx for idx in range(3) if idx != self.current_correct_idx]
        if self.current_secret_rule == 'MIN_SHAPES':
            profiles[self.current_correct_idx]['matrix'] = random.sample(range(9), 1)
            for w in wrong_indices: profiles[w]['matrix'] = random.sample(range(9), random.randint(4, 8))
        elif self.current_secret_rule == 'MAX_SHAPES':
            profiles[self.current_correct_idx]['matrix'] = random.sample(range(9), random.randint(7, 9))
            for w in wrong_indices: profiles[w]['matrix'] = random.sample(range(9), random.randint(1, 3))
        elif self.current_secret_rule == 'CENTER_OCCUPIED':
            profiles[self.current_correct_idx]['matrix'] = [4] + random.sample([0,1,2,3,5,6,7,8], random.randint(0, 3))
            for w in wrong_indices: profiles[w]['matrix'] = random.sample([0,1,2,3,5,6,7,8], random.randint(1, 4))
        elif self.current_secret_rule == 'UNIQUE_SHAPE':
            base_shape = random.choice(self.shapes)
            alt_shape = random.choice([s for s in self.shapes if s != base_shape])
            profiles[self.current_correct_idx]['shape'] = alt_shape
            profiles[self.current_correct_idx]['matrix'] = random.sample(range(9), random.randint(2, 5))
            for w in wrong_indices:
                profiles[w]['shape'] = base_shape
                profiles[w]['matrix'] = random.sample(range(9), random.randint(2, 5))
        elif self.current_secret_rule == 'UNIQUE_COLOR':
            base_color = random.choice(self.colors)
            alt_color = random.choice([c for c in self.colors if c != base_color])
            profiles[self.current_correct_idx]['color'] = alt_color
            profiles[self.current_correct_idx]['matrix'] = random.sample(range(9), random.randint(2, 5))
            for w in wrong_indices:
                profiles[w]['color'] = base_color
                profiles[w]['matrix'] = random.sample(range(9), random.randint(2, 5))
        elif self.current_secret_rule == 'EVEN_SHAPES':
            profiles[self.current_correct_idx]['matrix'] = random.sample(range(9), random.choice([2, 4, 6, 8]))
            for w in wrong_indices: profiles[w]['matrix'] = random.sample(range(9), random.choice([1, 3, 5, 7]))
        elif self.current_secret_rule == 'ODD_SHAPES':
            profiles[self.current_correct_idx]['matrix'] = random.sample(range(9), random.choice([1, 3, 5, 7]))
            for w in wrong_indices: profiles[w]['matrix'] = random.sample(range(9), random.choice([2, 4, 6, 8]))
        elif self.current_secret_rule == 'DIAGONAL_LINE':
            chosen_diag = random.choice([[0, 4, 8], [2, 4, 6]])
            profiles[self.current_correct_idx]['matrix'] = chosen_diag
            for w in wrong_indices:
                scrambled = random.sample(range(9), 3)
                while scrambled in [[0, 4, 8], [2, 4, 6]]: scrambled = random.sample(range(9), 3)
                profiles[w]['matrix'] = scrambled
        return profiles

    def render_matrix_grid(self, instance, *args):
        instance.canvas.clear()
        instance.canvas.after.clear()
        p = instance.sq_profile
        cell_w = instance.width / 3
        cell_h = instance.height / 3
        sz = min(cell_w, cell_h) * 0.55
        with instance.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=instance.pos, size=instance.size)
            if hasattr(instance, 'forced_fail_lock') and instance.forced_fail_lock:
                Color(0.8, 0.15, 0.15, 1)
                Rectangle(pos=instance.pos, size=instance.size)
                return
            Color(*p['color'])
            for pocket_idx in p['matrix']:
                r = pocket_idx // 3
                c = pocket_idx % 3
                cx = instance.x + (c * cell_w) + (cell_w / 2)
                cy = instance.y + ((2 - r) * cell_h) + (cell_h / 2)
                self.draw_vector_shape_geometry(p['shape'], cx, cy, sz)
        if hasattr(instance, 'forced_success_outline') and instance.forced_success_outline:
            with instance.canvas.after:
                Color(0.1, 0.8, 0.2, 1) 
                Line(rectangle=(instance.x + dp(2), instance.y + dp(2), instance.width - dp(4), instance.height - dp(4)), width=dp(3.5))

    def draw_vector_shape_geometry(self, stype, cx, cy, sz):
        if stype == 'SQUARE': Rectangle(pos=(cx - sz/2, cy - sz/2), size=(sz, sz))
        elif stype == 'TRIANGLE': Mesh(vertices=[cx, cy + sz/2, 0,0,  cx - sz/2, cy - sz/2, 0,0,  cx + sz/2, cy - sz/2, 0,0], indices=[0,1,2], mode='triangles')
        elif stype == 'CIRCLE': Ellipse(pos=(cx - sz/2, cy - sz/2), size=(sz, sz))
        elif stype == 'DIAMOND': Mesh(vertices=[cx, cy + sz/2, 0,0,  cx - sz/2, cy, 0,0,  cx, cy - sz/2, 0,0,  cx + sz/2, cy, 0,0], indices=[0,1,2, 0,2,3], mode='triangles')
        elif stype == 'CROSS':
            Rectangle(pos=(cx - sz/6, cy - sz/2), size=(sz/3, sz))
            Rectangle(pos=(cx - sz/2, cy - sz/6), size=(sz, sz/3))

    def handle_square_selection(self, instance):
        if not self.game_active or instance.row_index != self.row_counter: return
        current_row_data = self.history_rows[-1]
        if current_row_data['resolved']: return
        if instance.sq_index == current_row_data['correct_idx']:
            instance.forced_success_outline = True
            self.render_matrix_grid(instance)
            current_row_data['resolved'] = True
            self.correct_choices += 1
            self.score_label.text = f"PROGRESS: {self.correct_choices}/5"
            if self.correct_choices >= 5: self.trigger_victory()
            else: Clock.schedule_once(lambda dt: self.spawn_new_puzzle_row(), 0.25)
        else:
            trigger_haptic_feedback(0.08)
            instance.forced_fail_lock = True
            self.render_matrix_grid(instance)
            current_row_data['resolved'] = True
            Clock.schedule_once(lambda dt: self.spawn_new_puzzle_row(), 0.25)

    def trigger_victory(self):
        self.game_active = False
        if self.timer_event: Clock.unschedule(self.timer_event); self.timer_event = None
        formatted_rule = self.current_secret_rule.replace('_', ' ')
        self.title_label.text = "CORRECT!"
        self.title_label.color = (1, 0.84, 0, 1) 
        self.status_label.text = f"THE RULE WAS: {formatted_rule}"
        self.status_label.color = (0.04, 0.06, 0.17, 1) 
        with self.status_label.canvas.before:
            Color(1, 1, 1, 1) 
            self.status_reveal_bg = Rectangle(pos=(self.status_label.x, self.status_label.y), size=self.status_label.size)
        self.status_label.bind(
            pos=lambda inst, val: setattr(self.status_reveal_bg, 'pos', inst.pos) if self.status_reveal_bg else None,
            size=lambda inst, val: setattr(self.status_reveal_bg, 'size', inst.size) if self.status_reveal_bg else None
        )
        self.layout.remove_widget(self.title_label)
        self.layout.remove_widget(self.status_label)
        self.layout.add_widget(self.title_label)
        self.layout.add_widget(self.status_label)
        if self.play_help_row not in self.layout.children:
            self.start_btn.text = "NEXT RIDDLE"
            self.play_help_row.disabled = False
            self.layout.add_widget(self.play_help_row)

    def stop_game_engine(self):
        self.game_active = False
        if self.timer_event: Clock.unschedule(self.timer_event); self.timer_event = None
        self.rows_container.clear_widgets()
        self.status_label.canvas.before.clear()
        self.status_reveal_bg = None
        self.status_label.color = (0, 0.75, 1, 1)
        if self.play_help_row not in self.layout.children:
            self.start_btn.text = "PLAY AGAIN"
            self.play_help_row.disabled = False
            self.layout.add_widget(self.play_help_row)

class WaiterWaiterScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_active = False
        self.round_number = 1
        self.score = 0
        self.high_score = 0
        
        self.INITIAL_ROUND_TIMER = 60.0   
        self.CUSTOMER_WAIT_LIMIT = 5.0    
        self.EAT_TIME_MULTIPLIER = 2.0    

        self.global_timer = self.INITIAL_ROUND_TIMER
        self.total_customers = 15       
        self.seat_cooldown = 1.0        
        
        self.menu_items = [
            {'type': 'CIRCLE', 'color': (0.9, 0.2, 0.2, 1)},    
            {'type': 'SQUARE', 'color': (0.9, 0.5, 0.1, 1)},    
            {'type': 'TRIANGLE', 'color': (0.9, 0.8, 0.1, 1)},  
            {'type': 'DIAMOND', 'color': (0.9, 0.3, 0.6, 1)}    
        ]
        self.selected_menu_idx = None
        
        self.tables = []
        self.table_labels = []
        self.current_room = 0       
        self.room_view_x = 0.0      
        self.max_rooms = 1
        self.touch_start_pos = None

        self.engine_event = None

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.title_label = Label(
            text="WAITER WAITER", font_size=Scale.font(30), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.9}
        )
        self.layout.add_widget(self.title_label)

        self.timer_label = Label(
            text="TIME: 60s", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.24, 'center_y': 0.85}
        )
        self.layout.add_widget(self.timer_label)

        self.queue_label = Label(
            text="QUEUE: 15", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.76, 'center_y': 0.85}
        )
        self.layout.add_widget(self.queue_label)

        self.room_label = Label(
            text="ROOM: 1/1", font_size='10sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.80}
        )
        self.layout.add_widget(self.room_label)

        self.load_high_score()
        self.score_label = Label(
            text=f"ROUND: {self.round_number}  |  BEST: {self.high_score}", font_size='10sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 0.84, 0, 1), pos_hint={'center_x': 0.5, 'center_y': 0.02}
        )
        self.layout.add_widget(self.score_label)

        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        # 🟢 ROW WRAPPER REPLACEMENT
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint=(0.9,0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), size_hint_x=0.8,
            background_normal='', background_color=(0, 0.75, 1, 1)
        )
        self.start_btn.bind(on_release=self.start_game)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size='16sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)
        
        self.setup_tables()

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Waiter Waiter"
        placeholders = [
            "Tap a food icon in the bottom tray to load your waiter",
            "Match and tap tables requesting that specific dish",
            "Fulfill multi-item orders before customers leave",
            "Swipe left or right to manage new dining rooms"
        ]
        overlay = InstructionOverlay(game_name=game_name, rules_list=placeholders, close_callback=self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def on_pre_enter(self, *args):
        self.game_active = False
        self.title_label.text = "WAITER WAITER"
        self.title_label.color = (0, 0.75, 1, 1)
        if self.play_help_row not in self.layout.children:
            self.layout.add_widget(self.play_help_row)
        self.start_btn.text = "START GAME"
        self.play_help_row.disabled = False

    def on_leave(self):
        self.stop_game_engine()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def setup_tables(self):
        self.tables = []
        self.table_labels = []
        lbl_dim = Scale.min_dim(0.08)
        for room_idx in range(2):
            for r in range(3):
                for c in range(3):
                    self.tables.append({
                        'base_cx': 0, 'cy': 0, 'radius': 0, 
                        'state': 'EMPTY', 
                        'qty': 0, 'taps': 0, 'menu_idx': 0,
                        'wait_time': 0.0, 'eat_time': 0.0, 'max_eat': 0.0,
                        'grid_pos': (r, c), 'room_idx': room_idx
                    })
                    lbl = Label(
                        text="", 
                        font_size=Scale.font(14), 
                        font_name='assets/fonts/ARCADE_N.TTF', 
                        color=(1, 1, 1, 1), 
                        size_hint=(None, None), 
                        size=(lbl_dim, lbl_dim)
                    )
                    self.layout.add_widget(lbl)
                    self.table_labels.append(lbl)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        t_radius = Window.width * 0.11
        for idx, t in enumerate(self.tables):
            r, c = t['grid_pos']
            t['base_cx'] = Window.width * (0.22 + c * 0.28)
            t['cy'] = Window.height * (0.35 + r * 0.16)
            t['radius'] = t_radius
        self.draw_arena()
        
    def go_back_to_menu(self, instance):
        self.stop_game_engine()
        self.manager.current = 'menu'
        
    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('waiter_waiter_high', 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['waiter_waiter_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def start_game(self, instance):
        self.layout.remove_widget(self.play_help_row)
        self.round_number = 1
        self.score = 0
        self.start_round()

    def start_round(self):
        if self.play_help_row in self.layout.children:
            self.layout.remove_widget(self.play_help_row)
        self.global_timer = self.INITIAL_ROUND_TIMER
        self.max_rooms = 2 if self.round_number >= 4 else 1 
        self.total_customers = 10 + (self.round_number * 3)
        self.seat_cooldown = 1.0
        self.selected_menu_idx = None
        self.current_room = 0
        self.room_view_x = 0.0
        for idx, t in enumerate(self.tables):
            t['state'] = 'EMPTY'
            self.table_labels[idx].text = ""
        self.timer_label.text = f"TIME: {int(self.global_timer)}s"
        self.timer_label.color = (0, 0.75, 1, 1)
        self.queue_label.text = f"QUEUE: {self.total_customers}"
        self.score_label.text = f"ROUND: {self.round_number}  |  BEST: {self.high_score}"
        self.room_label.text = f"ROOM: 1/{self.max_rooms}"
        self.title_label.text = f"ROUND {self.round_number}"
        self.title_label.color = (0, 0.75, 1, 1)
        self.game_active = True
        if self.engine_event: Clock.unschedule(self.engine_event)
        self.engine_event = Clock.schedule_interval(self.game_loop, 1.0 / 60.0)

    def game_loop(self, dt):
        if not self.game_active: return
        self.global_timer -= dt
        if self.global_timer <= 0:
            self.trigger_game_over("TIME UP! YOU LOSE")
            trigger_haptic_feedback(0.08)
            return
        self.timer_label.text = f"TIME: {int(self.global_timer)}s"
        if self.global_timer < 15: self.timer_label.color = (0.9, 0.2, 0.2, 1)
        if self.total_customers > 0:
            self.seat_cooldown -= dt
            if self.seat_cooldown <= 0:
                empty_tables = [t for t in self.tables if t['state'] == 'EMPTY' and t['room_idx'] < self.max_rooms]
                if empty_tables:
                    t = random.choice(empty_tables)
                    t['state'] = 'WAITING'
                    t['qty'] = random.randint(1, 4)
                    t['taps'] = 0
                    t['menu_idx'] = random.randint(0, 3)
                    t['wait_time'] = self.CUSTOMER_WAIT_LIMIT 
                    t['eat_time'] = float(t['qty']) * self.EAT_TIME_MULTIPLIER 
                    t['max_eat'] = t['eat_time']
                    self.total_customers -= 1
                    self.queue_label.text = f"QUEUE: {self.total_customers}"
                    self.seat_cooldown = random.uniform(1.0, 2.2)
        active_tables_exist = False
        lbl_offset = Scale.min_dim(0.0)
        for idx, t in enumerate(self.tables):
            render_x = t['base_cx'] + (t['room_idx'] * Window.width) - self.room_view_x
            # Position text label right above the table center
            self.table_labels[idx].pos = (render_x - lbl_offset, t['cy'] + t['radius'] * 0.6)
            if t['room_idx'] >= self.max_rooms:
                self.table_labels[idx].text = ""
                continue
            if t['state'] == 'WAITING':
                active_tables_exist = True
                t['wait_time'] -= dt
                self.table_labels[idx].text = str(t['qty'] - t['taps'])
                if t['wait_time'] <= 0:
                    self.trigger_game_over("CUSTOMER WALKED OUT!")
                    trigger_haptic_feedback(0.08)
                    return
            elif t['state'] == 'EATING':
                active_tables_exist = True
                self.table_labels[idx].text = ""
                t['eat_time'] -= dt
                if t['eat_time'] <= 0:
                    t['state'] = 'EMPTY'
            else:
                self.table_labels[idx].text = ""
        if self.total_customers <= 0 and not active_tables_exist:
            self.trigger_victory()
            return
        self.draw_arena()

    def draw_arena(self):
        self.canvas.remove_group('waiter_shapes')
        if not self.game_active: return
        with self.canvas:
            k_width = Scale.width_pct(0.9)
            k_start_x = Scale.width_pct(0.05)
            k_y = Scale.height_pct(0.10)
            k_h = Scale.height_pct(0.08)
            slot_w = k_width / 4
            
            # Bottom Tray Items
            for i, menu in enumerate(self.menu_items):
                slot_x = k_start_x + (i * slot_w)
                if self.selected_menu_idx == i:
                    Color(1, 1, 1, 0.3, group='waiter_shapes')
                    Rectangle(pos=(slot_x, k_y), size=(slot_w, k_h), group='waiter_shapes')
                Color(1, 1, 1, 1, group='waiter_shapes')
                Line(rectangle=(slot_x, k_y, slot_w, k_h), width=dp(1.5), group='waiter_shapes')
                Color(*menu['color'], group='waiter_shapes')
                self.draw_vector_shape_geometry(menu['type'], slot_x + slot_w/2, k_y + k_h/2, min(slot_w, k_h) * 0.5, group='waiter_shapes')
            
            # Dining Tables & Order Icons (Rendered on top of tables)
            for idx, t in enumerate(self.tables):
                if t['room_idx'] >= self.max_rooms: continue
                render_x = t['base_cx'] + (t['room_idx'] * Window.width) - self.room_view_x
                tr = t['radius']
                
                # 1. Base Table Graphic
                Color(0.55, 0.27, 0.07, 1, group='waiter_shapes') 
                Ellipse(pos=(render_x - tr, t['cy'] - tr), size=(tr*2, tr*2), group='waiter_shapes')
                
                # 2. Waiting Timer & Requested Food Item Overlay
                if t['state'] == 'WAITING':
                    Color(1, 0.85, 0, 0.5, group='waiter_shapes')
                    angle = (t['wait_time'] / self.CUSTOMER_WAIT_LIMIT) * 360
                    Ellipse(pos=(render_x - tr, t['cy'] - tr), size=(tr*2, tr*2), angle_start=0, angle_end=angle, group='waiter_shapes')
                    Color(*self.menu_items[t['menu_idx']]['color'], group='waiter_shapes')
                    tiny_size = Scale.min_dim(0.045)
                    # Drawn cleanly above table surface center
                    self.draw_vector_shape_geometry(
                        self.menu_items[t['menu_idx']]['type'], 
                        render_x, 
                        t['cy'] + Scale.height_pct(0.0), 
                        tiny_size, 
                        group='waiter_shapes'
                    )
                elif t['state'] == 'EATING':
                    Color(0.1, 0.9, 0.2, 0.6, group='waiter_shapes')
                    angle = (t['eat_time'] / t['max_eat']) * 360
                    Ellipse(pos=(render_x - tr, t['cy'] - tr), size=(tr*2, tr*2), angle_start=0, angle_end=angle, group='waiter_shapes')
                    
            if self.current_room < self.max_rooms - 1:
                flash_opacity = abs(math.sin(self.global_timer * 5.0))
                Color(1, 0.15, 0.15, flash_opacity, group='waiter_shapes')
                ax, ay, aw = Scale.width_pct(0.92), Scale.height_pct(0.86), dp(14)
                Mesh(vertices=[ax, ay + aw, 0, 0, ax + aw, ay, 0, 0, ax, ay - aw, 0, 0], indices=[0, 1, 2], mode='triangles', group='waiter_shapes')

    def draw_vector_shape_geometry(self, stype, cx, cy, sz, group=None):
        if stype == 'SQUARE': Rectangle(pos=(cx - sz/2, cy - sz/2), size=(sz, sz), group=group)
        elif stype == 'TRIANGLE': Mesh(vertices=[cx, cy + sz/2, 0,0,  cx - sz/2, cy - sz/2, 0,0,  cx + sz/2, cy - sz/2, 0,0], indices=[0,1,2], mode='triangles', group=group)
        elif stype == 'CIRCLE': Ellipse(pos=(cx - sz/2, cy - sz/2), size=(sz, sz), group=group)
        elif stype == 'DIAMOND': Mesh(vertices=[cx, cy + sz/2, 0,0,  cx - sz/2, cy, 0,0,  cx, cy - sz/2, 0,0,  cx + sz/2, cy, 0,0], indices=[0,1,2, 0,2,3], mode='triangles', group=group)

    def on_touch_down(self, touch):
        if self.back_btn.collide_point(*touch.pos): return super().on_touch_down(touch)
        if not self.game_active: return super().on_touch_down(touch)
        self.touch_start_pos = touch.pos
        return True

    def on_touch_up(self, touch):
        if self.back_btn.collide_point(*touch.pos): return super().on_touch_up(touch)
        if not self.game_active or not self.touch_start_pos: return super().on_touch_up(touch)
        dx = touch.x - self.touch_start_pos[0]
        dy = touch.y - self.touch_start_pos[1]
        if abs(dx) > abs(dy) and abs(dx) > dp(40) and self.max_rooms > 1:
            if dx > 0 and self.current_room > 0:  
                self.current_room = 0
                Animation(room_view_x=0.0, duration=0.3, t='out_quad').start(self)
                self.room_label.text = f"ROOM: 1/{self.max_rooms}"
                self.touch_start_pos = None
                return True
            elif dx < 0 and self.current_room == 0:  
                self.current_room = 1
                Animation(room_view_x=float(Window.width), duration=0.3, t='out_quad').start(self)
                self.room_label.text = f"ROOM: 2/{self.max_rooms}"
                self.touch_start_pos = None
                return True
        k_y, k_h = Window.height * 0.10, Window.height * 0.08
        if k_y <= touch.y <= k_y + k_h:
            k_start_x = Window.width * 0.05
            slot_w = (Window.width * 0.9) / 4
            if touch.x >= k_start_x and touch.x <= k_start_x + (Window.width * 0.9):
                self.selected_menu_idx = int((touch.x - k_start_x) // slot_w)
                self.draw_arena()
                return True
        if self.selected_menu_idx is not None:
            for idx, t in enumerate(self.tables):
                if t['state'] == 'WAITING' and t['room_idx'] == self.current_room:
                    render_x = t['base_cx'] + (t['room_idx'] * Window.width) - self.room_view_x
                    dist = ((touch.x - render_x)**2 + (touch.y - t['cy'])**2)**0.5
                    if dist <= t['radius']:
                        if self.selected_menu_idx == t['menu_idx']:
                            t['taps'] += 1
                            if t['taps'] >= t['qty']: t['state'] = 'EATING'
                        else:
                            trigger_haptic_feedback(0.08)
                        return True
        self.touch_start_pos = None
        return super().on_touch_down(touch)

    def trigger_game_over(self, reason):
        self.stop_game_engine()
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
            self.title_label.text = "NEW HIGH SCORE!"
            self.title_label.color = (1, 0.84, 0, 1)
        else:
            self.title_label.text = reason
            self.title_label.color = (0.9, 0.2, 0.2, 1)
        self.score_label.text = f"ROUND: {self.round_number}  |  BEST: {self.high_score}"

    def trigger_victory(self):
        self.game_active = False
        if self.engine_event: Clock.unschedule(self.engine_event); self.engine_event = None
        self.score += 10 
        self.round_number += 1
        if self.score > self.high_score: self.high_score = self.score; self.save_high_score()
        self.title_label.text = "SHIFT COMPLETE!"
        self.title_label.color = (1, 0.84, 0, 1)
        for lbl in self.table_labels: lbl.text = ""
        if self.play_help_row in self.layout.children:
            self.layout.remove_widget(self.play_help_row)
        Clock.schedule_once(lambda dt: self.start_round(), 1.2)

    def stop_game_engine(self):
        self.game_active = False
        if self.engine_event: Clock.unschedule(self.engine_event); self.engine_event = None
        self.canvas.remove_group('waiter_shapes')
        for lbl in self.table_labels: lbl.text = ""
        self.start_btn.text = "RESTART GAME"
        if self.play_help_row not in self.layout.children:
            self.play_help_row.disabled = False
            self.layout.add_widget(self.play_help_row)
                       
class GateKeeperScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.round_number = 1
        self.score = 0
        self.high_score = 0
        self.time_remaining = 60.0
        self.game_active = False

        self.correct_passed = 0
        self.incorrect_leaked = 0

        self.shapes_pool = ['SQUARE', 'TRIANGLE', 'CIRCLE', 'DIAMOND']
        self.colors_map = {
            'SQUARE': (0.9, 0.2, 0.2, 1),     
            'TRIANGLE': (0.1, 0.7, 0.3, 1),   
            'CIRCLE': (0, 0.6, 0.9, 1),       
            'DIAMOND': (0.9, 0.7, 0, 1)       
        }
        self.target_shape = 'SQUARE'

        self.active_lanes_count = 3
        self.gate_states = [False] * 5        
        self.falling_shapes = []              
        self.lane_spawn_chains = [0] * 5      
        self.lane_chain_type = [None] * 5     

        self.timer_event = None
        self.game_event = None

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.load_high_score()

        self.title_label = Label(
            text="GATE KEEPER", font_size=Scale.font(30), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.9}
        )
        self.layout.add_widget(self.title_label)

        self.timer_label = Label(
            text="TIME: 60s", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.25, 'center_y': 0.85}
        )
        self.layout.add_widget(self.timer_label)

        self.target_label = Label(
            text="TARGET: SQUARE", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 1, 1, 1), pos_hint={'center_x': 0.70, 'center_y': 0.85}
        )
        self.layout.add_widget(self.target_label)

        self.stats_label = Label(
            text="PASS: 0  |  FAIL: 0", font_size='9sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.8}
        )
        self.layout.add_widget(self.stats_label)

        self.score_label = Label(
            text=f"ROUND: {self.round_number}  |  BEST: {self.high_score}", font_size='10sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 0.84, 0, 1), pos_hint={'center_x': 0.5, 'center_y': 0.03}
        )
        self.layout.add_widget(self.score_label)

        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        # 🟢 ROW WRAPPER REPLACEMENT
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint=(0.9,0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), size_hint_x=0.8,
            background_normal='', background_color=(0, 0.75, 1, 1)
        )
        self.start_btn.bind(on_release=self.start_game)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size='14sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Gate Keeper"
        placeholders = [
            "Check the header slot to identify what shapes are allowed through",
            "Tap any lane gate to activate or release its block",
            "Permit target shapes to pass through while locking out impermissible shapes"
        ]
        overlay = InstructionOverlay(game_name=game_name, rules_list=placeholders, close_callback=self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def on_enter(self):
        Window.bind(on_key_down=self.handle_keyboard_testing_inputs)

    def on_leave(self):
        Window.unbind(on_key_down=self.handle_keyboard_testing_inputs)
        self.stop_game_engine()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.draw_gate_keeper_canvas()

    def go_back_to_menu(self, instance):
        self.stop_game_engine()
        self.manager.current = 'menu'

    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('gate_keeper_high', 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['gate_keeper_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def handle_keyboard_testing_inputs(self, window, key, scancode, codepoint, modifier):
        if not self.game_active: return
        if 49 <= key <= 53:
            lane_idx = key - 49
            if lane_idx < self.active_lanes_count:
                self.gate_states[lane_idx] = not self.gate_states[lane_idx]
                self.draw_gate_keeper_canvas()

    def start_game(self, instance):
        self.layout.remove_widget(self.play_help_row)
        self.round_number = 1
        self.score = 0
        self.start_round()

    def start_round(self):
        if self.play_help_row in self.layout.children:
            self.layout.remove_widget(self.play_help_row)
        self.time_remaining = 60.0
        self.correct_passed = 0
        self.incorrect_leaked = 0
        self.falling_shapes = []
        self.gate_states = [False] * 5
        self.lane_spawn_chains = [0] * 5
        self.active_lanes_count = min(5, 3 + ((self.round_number - 1) // 3))
        self.target_shape = random.choice(self.shapes_pool)
        self.target_label.text = f"WANT: {self.target_shape}"
        self.target_label.color = self.colors_map[self.target_shape]
        self.timer_label.text = "TIME: 60s"
        self.stats_label.text = "PASS: 0  |  FAIL: 0"
        self.score_label.text = f"ROUND: {self.round_number}  |  BEST: {self.high_score}"
        self.title_label.text = f"ROUND {self.round_number}"
        self.title_label.color = (0, 0.75, 1, 1)
        self.game_active = True
        self.row_spawn_accumulator = 0.0
        if self.game_event: Clock.unschedule(self.game_event)
        self.game_event = Clock.schedule_interval(self.game_physics_tick, 1.0 / 60.0)

    def game_physics_tick(self, dt):
        if not self.game_active: return
        self.time_remaining -= dt
        if self.time_remaining <= 0:
            self.evaluate_round_end_condition()
            return
        self.timer_label.text = f"TIME: {int(self.time_remaining)}s"
        self.row_spawn_accumulator += dt
        if self.row_spawn_accumulator >= 0.65:
            self.row_spawn_accumulator = 0.0
            self.spawn_synchronized_shape_row()
        gate_y_line, gate_thickness, shape_speed, shape_kill_radius = Window.height * 0.18, Window.height * 0.07, (Window.height * 0.005) * (dt * 60.0), Window.width * 0.05
        for s in self.falling_shapes[:]:
            s['y'] -= shape_speed
            if s['y'] <= (gate_y_line + gate_thickness / 2 + shape_kill_radius):
                is_gate_open = self.gate_states[s['lane_idx']]
                if is_gate_open:
                    if s['type'] == self.target_shape: self.correct_passed += 1; self.score += 1
                    else: self.incorrect_leaked += 1; self.score = max(0, self.score - 1); trigger_haptic_feedback(0.08)
                    self.falling_shapes.remove(s)
                else:
                    if s['type'] == self.target_shape: self.incorrect_leaked += 1; self.score = max(0, self.score - 1); trigger_haptic_feedback(0.08)
                    self.falling_shapes.remove(s)
                self.stats_label.text = f"PASS: {self.correct_passed}  |  FAIL: {self.incorrect_leaked}"
                if self.score > self.high_score:
                    self.high_score = self.score
                    self.save_high_score()
                    self.score_label.text = f"ROUND: {self.round_number}  |  BEST: {self.high_score}"
        self.draw_gate_keeper_canvas()

    def spawn_synchronized_shape_row(self):
        for lane in range(self.active_lanes_count):
            if self.lane_spawn_chains[lane] > 0:
                shape_type = self.lane_chain_type[lane]
                self.lane_spawn_chains[lane] -= 1
            else:
                if random.random() < 0.45:
                    self.lane_spawn_chains[lane] = random.randint(1, 3)
                    self.lane_chain_type[lane] = random.choice(self.shapes_pool)
                    shape_type = self.lane_chain_type[lane]
                    self.lane_spawn_chains[lane] -= 1
                else: continue
            self.falling_shapes.append({'lane_idx': lane, 'y': Window.height + dp(20), 'type': shape_type})
            
    def draw_vector_shape_geometry(self, stype, cx, cy, sz, group=None):
        if stype == 'SQUARE':
            Rectangle(pos=(cx - sz/2, cy - sz/2), size=(sz, sz), group=group)
        elif stype == 'TRIANGLE':
            Mesh(vertices=[cx, cy + sz/2, 0,0,  cx - sz/2, cy - sz/2, 0,0,  cx + sz/2, cy - sz/2, 0,0], indices=[0,1,2], mode='triangles', group=group)
        elif stype == 'CIRCLE':
            Ellipse(pos=(cx - sz/2, cy - sz/2), size=(sz, sz), group=group)
        elif stype == 'DIAMOND':
            Mesh(vertices=[cx, cy + sz/2, 0,0,  cx - sz/2, cy, 0,0,  cx, cy - sz/2, 0,0,  cx + sz/2, cy, 0,0], indices=[0,1,2, 0,2,3], mode='triangles', group=group)

    def on_touch_down(self, touch):
        if self.back_btn.collide_point(*touch.pos): return super().on_touch_down(touch)
        if not self.game_active: return super().on_touch_down(touch)
        lane_w = Window.width / self.active_lanes_count
        clicked_lane = int(touch.x // lane_w)
        if 0 <= clicked_lane < self.active_lanes_count:
            self.gate_states[clicked_lane] = not self.gate_states[clicked_lane]
            self.draw_gate_keeper_canvas()
            return True
        return super().on_touch_down(touch)

    def draw_gate_keeper_canvas(self):
        self.canvas.remove_group('gatekeeper_shapes')
        self.canvas.before.remove_group('gatekeeper_shapes')
        if not self.game_active: return
        lane_w, gate_y_line, gate_thickness, shape_sz = Window.width / self.active_lanes_count, Window.height * 0.18, Window.height * 0.07, Window.width * 0.045
        with self.canvas.before:
            for i in range(1, self.active_lanes_count):
                Color(0, 0.75, 1, 0.15, group='gatekeeper_shapes')
                Line(points=[i * lane_w, 0, i * lane_w, Window.height], width=dp(1.2), group='gatekeeper_shapes')
            for s in self.falling_shapes:
                Color(*self.colors_map[s['type']], group='gatekeeper_shapes')
                cx = (s['lane_idx'] * lane_w) + (lane_w / 2)
                self.draw_vector_shape_geometry(s['type'], cx, s['y'], shape_sz, group='gatekeeper_shapes')
            for lane in range(self.active_lanes_count):
                is_open, lx = self.gate_states[lane], lane * lane_w
                if is_open:
                    Color(0.1, 0.9, 0.3, 0.25, group='gatekeeper_shapes')
                    Rectangle(pos=(lx + dp(2), gate_y_line - gate_thickness/2), size=(lane_w - dp(4), gate_thickness), group='gatekeeper_shapes')
                    Color(0.1, 0.9, 0.3, 0.6, group='gatekeeper_shapes')
                    Line(rectangle=(lx + dp(2), gate_y_line - gate_thickness/2, lane_w - dp(4), gate_thickness), width=dp(1.5), group='gatekeeper_shapes')
                else:
                    Color(0.9, 0.15, 0.2, 1, group='gatekeeper_shapes')
                    Rectangle(pos=(lx + dp(2), gate_y_line - gate_thickness/2), size=(lane_w - dp(4), gate_thickness), group='gatekeeper_shapes')
                    Color(0.04, 0.06, 0.17, 0.5, group='gatekeeper_shapes')
                    Rectangle(pos=((lx + lane_w/2) - dp(8), gate_y_line - dp(4)), size=(dp(16), dp(8)), group='gatekeeper_shapes')

    def evaluate_round_end_condition(self):
        self.game_active = False
        if self.game_event: Clock.unschedule(self.game_event); self.game_event = None
        if self.correct_passed > 0 and self.incorrect_leaked < (self.correct_passed / 2.0):
            self.round_number += 1
            self.title_label.text = "DEFENSE SECURED!"
            self.title_label.color = (0.1, 0.9, 0.3, 1)
            Clock.schedule_once(lambda dt: self.start_round(), 1.5)
        else:
            self.trigger_game_over()
            trigger_haptic_feedback(0.08)

    def check_achievements(self):
        """Unlocks achievements based on completed flawless rounds."""
        if self.incorrect_leaked == 0:
            completed_rounds = self.round_number - 1
            if completed_rounds >= 3:
                self.unlock_achievement('gatekeeper_flawless_3')
            if completed_rounds >= 6:
                self.unlock_achievement('gatekeeper_flawless_6')
            if completed_rounds >= 9:
                self.unlock_achievement('gatekeeper_flawless_9')

    def unlock_achievement(self, achievement_id):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            achievements = data.get('achievements', {})
            if not achievements.get(achievement_id, False):
                achievements[achievement_id] = True
                data['achievements'] = achievements
                
                with open('save_data.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f)
                
                trigger_haptic_feedback(0.2)
        except Exception:
            pass

    def evaluate_round_end_condition(self):
        self.game_active = False
        if self.game_event: 
            Clock.unschedule(self.game_event)
            self.game_event = None
            
        if self.correct_passed > 0 and self.incorrect_leaked < (self.correct_passed / 2.0):
            self.round_number += 1
            self.title_label.text = "DEFENSE SECURED!"
            self.title_label.color = (0.1, 0.9, 0.3, 1)
            
            # Check flawless achievements on each round completion!
            self.check_achievements()
            
            Clock.schedule_once(lambda dt: self.start_round(), 1.5)
        else:
            self.trigger_game_over()
            trigger_haptic_feedback(0.08)
    
    def trigger_game_over(self):
        self.game_active = False
        if self.game_event: Clock.unschedule(self.game_event); self.game_event = None
        self.check_achievements()
        self.canvas.remove_group('gatekeeper_shapes')
        self.title_label.text = "GATES BREACHED!"
        self.title_label.color = (0.9, 0.2, 0.2, 1)
        self.timer_label.text = f"FINAL PASS: {self.correct_passed}"
        self.stats_label.text = f"TOO MANY FAILS: {self.incorrect_leaked}"
        self.start_btn.text = "REPAIR GATES"
        if self.play_help_row not in self.layout.children:
            self.layout.add_widget(self.play_help_row)

    def stop_game_engine(self):
        self.game_active = False
        if self.game_event: Clock.unschedule(self.game_event); self.game_event = None
        self.canvas.before.remove_group('gatekeeper_shapes')
        self.falling_shapes = []
        self.gate_states = [False] * 5
        self.lane_spawn_chains = [0] * 5
        self.start_btn.text = "DEFEND GATES"
        if self.play_help_row not in self.layout.children:
            self.layout.add_widget(self.play_help_row)

class DropOffScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.round_number = 1
        self.score = 0
        self.high_score = 0
        self.time_remaining = 60.0
        self.game_active = False

        self.hidden_inventory = {'SQUARE': 0, 'CIRCLE': 0}
        self.mistakes_count = 0
        self.MAX_MISTAKES = 3

        self.scroll_y_offset = 0.0
        self.stop_timer = 0.0
        self.is_moving_between_stops = False
        self.flash_red_timer = 0.0
        self.show_inventory_hint = False
        self.recent_spawns = [] 

        self.current_mailbox = None 
        self.next_mailbox = None    

        self.game_event = None
        self.load_high_score()

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.title_label = Label(
            text="DROP OFF", font_size=Scale.font(30), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.95}
        )
        self.layout.add_widget(self.title_label)

        self.timer_label = Label(
            text="TIME: 60s", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.25, 'center_y': 0.90}
        )
        self.layout.add_widget(self.timer_label)

        self.mistake_label = Label(
            text="MISTAKES: 0/3", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.9, 0.2, 0.2, 1), pos_hint={'center_x': 0.75, 'center_y': 0.90}
        )
        self.layout.add_widget(self.mistake_label)

        self.inventory_hint_label = Label(
            text="", font_size='10sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 0.4, 0.4, 1), pos_hint={'center_x': 0.5, 'center_y': 0.84}
        )
        self.layout.add_widget(self.inventory_hint_label)

        self.score_label = Label(
            text=f"ROUND: {self.round_number}  |  BEST: {self.high_score}", font_size='10sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 0.84, 0, 1), pos_hint={'center_x': 0.5, 'center_y': 0.03}
        )
        self.layout.add_widget(self.score_label)

        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        # 🟢 ROW WRAPPER REPLACEMENT
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint=(0.9,0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), size_hint_x=0.8,
            background_normal='', background_color=(0, 0.75, 1, 1)
        )
        self.start_btn.bind(on_release=self.start_game)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size='14sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Drop Off"
        placeholders = [
            "Tap left arrow box stations to pick up cargo",
            "Tap right arrow box stations to unload stock if it matches the order",
            "Keep a mental tally of your inventory",
            "Three delivery order mistakes will completely break down the van"
        ]
        overlay = InstructionOverlay(game_name=game_name, rules_list=placeholders, close_callback=self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def on_pre_enter(self, *args):
        self.stop_game_engine()
        if self.play_help_row not in self.layout.children:
            self.layout.add_widget(self.play_help_row)
        self.title_label.text = "DROP OFF"
        self.title_label.color = (0, 0.75, 1, 1)
        self.timer_label.text = "TIME: 60s"
        self.mistake_label.text = "MISTAKES: 0/3"
        self.inventory_hint_label.text = ""
        self.score_label.text = f"ROUND: {self.round_number}  |  BEST: {self.high_score}"

    def on_leave(self, *args):
        self.stop_game_engine()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.draw_drop_off_canvas()

    def go_back_to_menu(self, instance):
        self.manager.current = 'menu'

    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('drop_off_high', 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['drop_off_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def start_game(self, instance):
        self.layout.remove_widget(self.play_help_row)
        self.round_number = 1
        self.score = 0
        self.start_round()

    def start_round(self):
        if self.play_help_row in self.layout.children:
            self.layout.remove_widget(self.play_help_row)
        self.time_remaining, self.mistakes_count, self.hidden_inventory, self.recent_spawns = 60.0, 0, {'SQUARE': 0, 'CIRCLE': 0}, []
        self.scroll_y_offset, self.flash_red_timer, self.show_inventory_hint = 0.0, 0.0, False
        self.inventory_hint_label.text = ""
        self.timer_label.text = "TIME: 60s"
        self.mistake_label.text = "MISTAKES: 0/3"
        self.score_label.text = f"ROUND: {self.round_number}  |  BEST: {self.high_score}"
        self.title_label.text = f"ROUND {self.round_number}"
        self.current_mailbox = self.generate_procedural_mailbox_stop(y_pos=Window.height * 0.45)
        self.next_mailbox = self.generate_procedural_mailbox_stop(y_pos=Window.height * 0.95)
        self.stop_timer, self.is_moving_between_stops = 3.5, False
        self.game_active = True
        if self.game_event: Clock.unschedule(self.game_event)
        self.game_event = Clock.schedule_interval(self.game_physics_tick, 1.0 / 60.0)

    def generate_procedural_mailbox_stop(self, y_pos):
        has_stock = self.hidden_inventory['SQUARE'] > 0 or self.hidden_inventory['CIRCLE'] > 0
        if self.recent_spawns.count('PICK_UP') >= 2 and has_stock: 
            mode = 'DROP_OFF'
        elif self.recent_spawns.count('DROP_OFF') >= 2 or not has_stock: 
            mode = 'PICK_UP'
        else: 
            mode = random.choice(['PICK_UP', 'DROP_OFF'])
            
        self.recent_spawns.append(mode)
        if len(self.recent_spawns) > 3: 
            self.recent_spawns.pop(0)
            
        items = []
        if mode == 'PICK_UP':
            qty = random.randint(2, 4)
            for _ in range(qty): 
                items.append(random.choice(['SQUARE', 'CIRCLE']))
        else:
            is_deficit_order = random.random() < 0.25
            available_choices = []
            if self.hidden_inventory['SQUARE'] > 0: 
                available_choices.append('SQUARE')
            if self.hidden_inventory['CIRCLE'] > 0: 
                available_choices.append('CIRCLE')
            if not available_choices: 
                available_choices = ['SQUARE', 'CIRCLE']
                
            qty = random.randint(1, 3)
            for _ in range(qty):
                chosen_item = random.choice(available_choices)
                items.append(chosen_item)
                if not is_deficit_order:
                    if items.count(chosen_item) >= self.hidden_inventory.get(chosen_item, 0) and chosen_item in available_choices:
                        available_choices.remove(chosen_item)
                        if not available_choices:
                            available_choices = ['SQUARE', 'CIRCLE']

        return {'y': y_pos, 'mode': mode, 'items': items, 'processed': False}

    def game_physics_tick(self, dt):
        if not self.game_active: return
        self.time_remaining -= dt
        if self.time_remaining <= 0: self.trigger_victory_advance(); return
        self.timer_label.text = f"TIME: {int(self.time_remaining)}s"
        if self.flash_red_timer > 0:
            self.flash_red_timer -= dt
            if self.flash_red_timer <= 0: self.show_inventory_hint, self.inventory_hint_label.text = False, ""
        if self.is_moving_between_stops:
            scroll_speed = ((Window.height * 0.5) / 0.8) * dt 
            self.scroll_y_offset += scroll_speed
            self.current_mailbox['y'] -= scroll_speed
            self.next_mailbox['y'] -= scroll_speed
            if self.next_mailbox['y'] <= Window.height * 0.45:
                diff = (Window.height * 0.45) - self.next_mailbox['y']
                self.current_mailbox['y'] -= diff
                self.next_mailbox['y'] = Window.height * 0.45
                self.current_mailbox = self.next_mailbox
                self.next_mailbox = self.generate_procedural_mailbox_stop(y_pos=Window.height * 0.95)
                self.is_moving_between_stops, self.stop_timer = False, 2.5
        else:
            self.stop_timer -= dt
            if self.stop_timer <= 0: self.is_moving_between_stops = True
        self.draw_drop_off_canvas()

    def on_touch_down(self, touch):
        if self.back_btn.collide_point(*touch.pos): return super().on_touch_down(touch)
        if not self.game_active or self.is_moving_between_stops: return super().on_touch_down(touch)
        box_left, box_right, box_bottom, box_top = Window.width * 0.52, Window.width * 0.65, self.current_mailbox['y'] - dp(25), self.current_mailbox['y'] + dp(25)
        if box_left <= touch.x <= box_right and box_bottom <= touch.y <= box_top:
            if self.current_mailbox['processed']: return True
            mb = self.current_mailbox
            if mb['mode'] == 'PICK_UP':
                for item in mb['items']: self.hidden_inventory[item] += 1
                mb['processed'] = True
                self.score += len(mb['items'])
            elif mb['mode'] == 'DROP_OFF':
                req_counts = {'SQUARE': mb['items'].count('SQUARE'), 'CIRCLE': mb['items'].count('CIRCLE')}
                if self.hidden_inventory['SQUARE'] >= req_counts['SQUARE'] and self.hidden_inventory['CIRCLE'] >= req_counts['CIRCLE']:
                    self.hidden_inventory['SQUARE'] -= req_counts['SQUARE']
                    self.hidden_inventory['CIRCLE'] -= req_counts['CIRCLE']
                    mb['processed'] = True
                    self.score += len(mb['items']) * 2 
                else: self.trigger_mistake_penalty()
            self.score_label.text = f"SCORE: {self.score}"
            if self.score > self.high_score: self.high_score = self.score; self.save_high_score()
            self.draw_drop_off_canvas()
            return True
        return super().on_touch_down(touch)

    def trigger_mistake_penalty(self):
        trigger_haptic_feedback(0.08)
        self.mistakes_count += 1
        self.mistake_label.text = f"MISTAKES: {self.mistakes_count}/3"
        self.flash_red_timer, self.show_inventory_hint = 2.0, True
        self.inventory_hint_label.text = f"STOCK -> SQ: {self.hidden_inventory['SQUARE']} | CI: {self.hidden_inventory['CIRCLE']}"
        if self.mistakes_count >= self.MAX_MISTAKES:
            self.trigger_game_over()

    def draw_drop_off_canvas(self):
        self.canvas.before.remove_group('dropoff_shapes')
        if not self.game_active: return
        road_w, van_w = Window.width * 0.5, Window.width * 0.14
        van_h = van_w * 1.5 
        with self.canvas.before:
            Color(0.22, 0.24, 0.26, 1, group='dropoff_shapes')
            Rectangle(pos=(0, 0), size=(road_w, Window.height), group='dropoff_shapes')
            Color(0.9, 0.75, 0.0, 1, group='dropoff_shapes')
            stripe_h, stripe_gap = dp(35), dp(25)
            total_stripe_module = stripe_h + stripe_gap
            y_start = (self.scroll_y_offset % total_stripe_module) - total_stripe_module
            for y in range(int(y_start), int(Window.height), int(total_stripe_module)):
                Rectangle(pos=(road_w / 2 - dp(3), y), size=(dp(6), stripe_h), group='dropoff_shapes')
            Color(0.2, 0.55, 0.3, 1, group='dropoff_shapes')
            Rectangle(pos=(road_w, 0), size=(road_w, Window.height), group='dropoff_shapes')
            for box in [self.current_mailbox, self.next_mailbox]:
                if not box: continue
                Color(0.7, 0.72, 0.75, 1, group='dropoff_shapes')
                Rectangle(pos=(road_w, box['y'] - dp(8)), size=(road_w, dp(16)), group='dropoff_shapes')
                if not box['processed']:
                    Color(0.85, 0.15, 0.15, 1, group='dropoff_shapes')
                    Rectangle(pos=(road_w + dp(10), box['y'] - dp(12)), size=(dp(24), dp(24)), group='dropoff_shapes')
                    Color(1, 1, 1, 1, group='dropoff_shapes')
                    if box['mode'] == 'PICK_UP':
                        Line(points=[road_w + dp(28), box['y'], road_w + dp(16), box['y']], width=dp(2), group='dropoff_shapes')
                        Line(points=[road_w + dp(22), box['y'] + dp(6), road_w + dp(16), box['y'], road_w + dp(22), box['y'] - dp(6)], width=dp(2), group='dropoff_shapes')
                    else:
                        Line(points=[road_w + dp(16), box['y'], road_w + dp(28), box['y']], width=dp(2), group='dropoff_shapes')
                        Line(points=[road_w + dp(22), box['y'] + dp(6), road_w + dp(28), box['y'], road_w + dp(22), box['y'] - dp(6)], width=dp(2), group='dropoff_shapes')
                    Color(0.65, 0.45, 0.25, 1, group='dropoff_shapes')
                    item_sz, start_items_x = dp(26), road_w + dp(50)
                    for i, itype in enumerate(box['items']):
                        cx = start_items_x + (i * dp(32))
                        if itype == 'SQUARE': Rectangle(pos=(cx - item_sz/2, box['y'] - item_sz/2), size=(item_sz, item_sz), group='dropoff_shapes')
                        else: Ellipse(pos=(cx - item_sz/2, box['y'] - item_sz/2), size=(item_sz, item_sz), group='dropoff_shapes')
            if self.flash_red_timer > 0: Color(0.9, 0.15, 0.15, 1, group='dropoff_shapes')
            else: Color(1, 1, 1, 1, group='dropoff_shapes')
            van_x, van_y = (road_w / 2) - (van_w / 2), (Window.height * 0.45) - (van_h / 2)
            Rectangle(pos=(van_x, van_y), size=(van_w, van_h), group='dropoff_shapes')

    def trigger_victory_advance(self):
        self.game_active = False
        if self.game_event: Clock.unschedule(self.game_event); self.game_event = None
        self.round_number += 1
        self.title_label.text = "SHIFT LOG SECURED!"
        self.title_label.color = (0.1, 0.9, 0.3, 1)
        Clock.schedule_once(lambda dt: self.start_round(), 1.5)

    def trigger_game_over(self):
        self.game_active = False
        if self.game_event: Clock.unschedule(self.game_event); self.game_event = None
        self.canvas.before.remove_group('dropoff_shapes')
        self.title_label.text = "VAN BROKEN DOWN!"
        self.title_label.color = (0.9, 0.2, 0.2, 1)
        self.inventory_hint_label.text = "MISTAKE LIMIT BREACHED"
        self.start_btn.text = "RELOAD SHIFT"
        if self.play_help_row not in self.layout.children:
            self.layout.add_widget(self.play_help_row)
            
    def stop_game_engine(self):
        self.game_active = False
        if self.game_event: Clock.unschedule(self.game_event); self.game_event = None
        self.canvas.before.remove_group('dropoff_shapes')
        self.hidden_inventory = {'SQUARE': 0, 'CIRCLE': 0}
        self.current_mailbox = None
        self.next_mailbox = None
        self.recent_spawns = []
        
class DynamicCircle(Widget):
    """A custom widget that handles its own canvas drawing for the breathing circle."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(0.47, 0.87, 0.47, 1)  # Solid Pastel Green
            self.ellipse = Ellipse(pos=self.pos, size=self.size)
        # Bind positional and size changes to update the drawn ellipse
        self.bind(pos=self.update_graphics, size=self.update_graphics)

    def update_graphics(self, *args):
        self.ellipse.pos = self.pos
        self.ellipse.size = self.size


class ZenBreathingScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session_time = 180  # 3 minutes default
        self.time_remaining = self.session_time
        self.is_active = False
        self.current_state = 0
        self.timer_event = None
        self.current_anim = None
        
        # Breathing Exercises Carousel Registry (Presets + Custom)
        self.exercise_keys = [
            "4-4-4-4",
            "4-7-8",
            "5.5-5.5",
            "2-4 (pursed lips)",
            "CUSTOM"
        ]
        self.selected_index = 0
        
        # Default Custom Timers (Inhale, Hold In, Exhale, Hold Out)
        self.custom_timers = [4.0, 4.0, 4.0, 4.0]
        self.load_custom_timers()
        
        # Preset Timings Map
        self.profiles = {
            "4-4-4-4": (4.0, 4.0, 4.0, 4.0),
            "4-7-8": (4.0, 7.0, 8.0, 0.0),
            "5.5-5.5": (5.5, 0.0, 5.5, 0.0),
            "2-4 (pursed lips)": (2.0, 0.0, 4.0, 0.0)
        }
        
        # --- BACKGROUND ---
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)  # Deep Cosmic Background
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        # Main container
        self.main_layout = RelativeLayout()
        self.add_widget(self.main_layout)
        
        # --- UI COMPONENTS ---
        self.timer_label = Label(
            text="3:00",
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size='36sp',
            color=(1, 1, 1, 1),
            pos_hint={'center_x': 0.5, 'top': 0.95},
            size_hint=(1, 0.1)
        )
        self.main_layout.add_widget(self.timer_label)
        
        self.instruction_label = Label(
            text="READY",
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size='18sp',
            color=(0.47, 0.87, 0.47, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.78},
            size_hint=(1, 0.1)
        )
        self.main_layout.add_widget(self.instruction_label)
        
        # --- BREATHING VISUALS ---
        self.breathing_area = RelativeLayout(
            size_hint=(None, None),
            size=(dp(230), dp(250)),
            pos_hint={'center_x': 0.5, 'center_y': 0.53}
        )
        
        # Static Diaphragm Circle (Centered 1:1 Aspect Ratio Circle)
        with self.breathing_area.canvas.before:
            Color(0.47, 0.87, 0.47, 0.15)  # Soft Pastel Green Fill
            self.diaphragm = Ellipse()
        self.breathing_area.bind(size=self._update_diaphragm, pos=self._update_diaphragm)
        
        # Dynamic Expanding Circle
        self.dynamic_circle = DynamicCircle(
            size_hint=(None, None),
            size=(dp(50), dp(50))
        )
        self.dynamic_circle.pos = (dp(115) - dp(25), dp(125) - dp(25))
        self.breathing_area.add_widget(self.dynamic_circle)
        
        self.main_layout.add_widget(self.breathing_area)
        
        # --- CUSTOM TIMERS CONTROL PANEL ---
        self.custom_panel = BoxLayout(
            orientation='horizontal',
            size_hint=(0.95, 0.08),
            pos_hint={'center_x': 0.5, 'y': 0.25},
            spacing=dp(4),
            opacity=0,
            disabled=True
        )
        self.custom_labels = []
        self.build_custom_panel_ui()
        self.main_layout.add_widget(self.custom_panel)

        # --- CONTROLS ---
        self.controls_layout = BoxLayout(
            orientation='vertical',
            size_hint=(0.85, 0.2),
            pos_hint={'center_x': 0.5, 'y': 0.04},
            spacing=dp(10)
        )
        
        # Multi-state Play/End Action Button
        self.play_btn = Button(
            text="START SESSION",
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size=Scale.font(16),
            background_normal='',
            background_color=(0.1, 0.6, 0.3, 1)
        )
        self.play_btn.bind(on_release=self.toggle_session)
        
        # --- Custom [<] Exercise [>] Selector Layout ---
        self.selector_layout = BoxLayout(
            orientation='horizontal',
            size_hint=(1, 0.5),
            spacing=dp(5)
        )
        
        self.prev_btn = Button(
            text="<",
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size=Scale.font(16),
            size_hint=(0.2, 1),
            background_normal='',
            background_color=(0.2, 0.2, 0.3, 1)
        )
        self.prev_btn.bind(on_release=self._prev_exercise)
        
        self.exercise_label = Label(
            text=self.exercise_keys[self.selected_index],
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size=Scale.font(12),
            color=(1, 1, 1, 1),
            size_hint=(0.6, 1)
        )
        
        self.next_btn = Button(
            text=">",
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size=Scale.font(16),
            size_hint=(0.2, 1),
            background_normal='',
            background_color=(0.2, 0.2, 0.3, 1)
        )
        self.next_btn.bind(on_release=self._next_exercise)
        
        self.selector_layout.add_widget(self.prev_btn)
        self.selector_layout.add_widget(self.exercise_label)
        self.selector_layout.add_widget(self.next_btn)
        
        self.controls_layout.add_widget(self.play_btn)
        self.controls_layout.add_widget(self.selector_layout)
        self.main_layout.add_widget(self.controls_layout)
        
        # --- BACK BUTTON ---
        self.back_btn = Button(
            text="< MENU",
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size=Scale.font(15),
            size_hint=(0.25, 0.05),
            pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='',
            background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self._go_back)
        self.main_layout.add_widget(self.back_btn)

    def load_custom_timers(self):
        """Loads user custom breathing values from local JSON save."""
        self.custom_timers = [
            web_load_game_data('custom_inhale', 4.0),
            web_load_game_data('custom_hold_in', 4.0),
            web_load_game_data('custom_exhale', 4.0),
            web_load_game_data('custom_hold_out', 4.0)
        ]

    def save_custom_timers(self):
        """Saves custom breathing values to JSON."""
        web_save_game_data('custom_inhale', self.custom_timers[0])
        web_save_game_data('custom_hold_in', self.custom_timers[1])
        web_save_game_data('custom_exhale', self.custom_timers[2])
        web_save_game_data('custom_hold_out', self.custom_timers[3])

    def build_custom_panel_ui(self):
        """Creates 4 quick adjusters: IN, HOLD, OUT, HOLD."""
        labels = ["IN", "HOLD", "OUT", "HOLD"]
        
        for idx in range(4):
            box = BoxLayout(orientation='vertical', spacing=dp(2))
            
            lbl = Label(
                text=f"{labels[idx]}\n{self.custom_timers[idx]}s",
                font_name="assets/fonts/ARCADE_N.TTF",
                font_size='7sp',
                color=(0, 0.75, 1, 1),
                halign='center'
            )
            lbl.bind(size=lbl.setter('text_size'))
            self.custom_labels.append(lbl)
            
            btn_row = BoxLayout(orientation='horizontal', spacing=dp(2))
            
            minus_btn = Button(
                text="-", font_name="assets/fonts/ARCADE_N.TTF", font_size='12sp',
                background_normal='', background_color=(0.8, 0.2, 0.2, 1)
            )
            minus_btn.bind(on_release=lambda x, i=idx: self.adjust_custom_val(i, -0.5))
            
            plus_btn = Button(
                text="+", font_name="assets/fonts/ARCADE_N.TTF", font_size='12sp',
                background_normal='', background_color=(0.1, 0.6, 0.3, 1)
            )
            plus_btn.bind(on_release=lambda x, i=idx: self.adjust_custom_val(i, 0.5))
            
            btn_row.add_widget(minus_btn)
            btn_row.add_widget(plus_btn)
            
            box.add_widget(lbl)
            box.add_widget(btn_row)
            self.custom_panel.add_widget(box)

    def adjust_custom_val(self, timer_idx, delta):
        if self.is_active: return
        min_val = 0.0 if timer_idx in [1, 3] else 1.0
        new_val = round(max(min_val, min(20.0, self.custom_timers[timer_idx] + delta)), 1)
        
        self.custom_timers[timer_idx] = new_val
        self.save_custom_timers()
        
        labels = ["IN", "HOLD", "OUT", "HOLD"]
        self.custom_labels[timer_idx].text = f"{labels[timer_idx]}\n{new_val}s"
        trigger_haptic_feedback(0.04)

    def get_current_timings(self):
        key = self.exercise_keys[self.selected_index]
        if key == "CUSTOM":
            return tuple(self.custom_timers)
        return self.profiles[key]

    def update_exercise_ui(self):
        key = self.exercise_keys[self.selected_index]
        self.exercise_label.text = key

        if key == "CUSTOM" and not self.is_active:
            self.custom_panel.opacity = 1
            self.custom_panel.disabled = False
        else:
            self.custom_panel.opacity = 0
            self.custom_panel.disabled = True

    # --- CANVAS BINDING HELPERS ---
    def _update_bg(self, instance, *args):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def _update_diaphragm(self, instance, *args):
        diameter = min(instance.width, instance.height)
        self.diaphragm.size = (diameter, diameter)
        self.diaphragm.pos = (
            (instance.width - diameter) / 2,
            (instance.height - diameter) / 2
        )

    def _go_back(self, instance):
        self.end_session()
        self.manager.current = 'menu'

    # --- EXERCISE SELECTOR HELPERS ---
    def _prev_exercise(self, instance):
        if self.is_active: return
        self.selected_index = (self.selected_index - 1) % len(self.exercise_keys)
        self.update_exercise_ui()

    def _next_exercise(self, instance):
        if self.is_active: return
        self.selected_index = (self.selected_index + 1) % len(self.exercise_keys)
        self.update_exercise_ui()

    # --- GAME LOGIC & SESSION TOGGLE ---
    def toggle_session(self, instance=None):
        """Starts or interrupts a breathing session on demand."""
        if not self.is_active:
            self.start_session()
        else:
            self.end_session(interrupted=True)

    def start_session(self):
        self.is_active = True
        self.time_remaining = self.session_time
        self.timer_label.text = "3:00"
        
        # Update Action Button to RED "END SESSION"
        self.play_btn.text = "END SESSION"
        self.play_btn.background_color = (0.8, 0.2, 0.2, 1)

        # Lock carousel & custom panels while active
        self.selector_layout.disabled = True
        self.custom_panel.opacity = 0
        self.custom_panel.disabled = True

        self.timer_event = Clock.schedule_interval(self.update_timer, 1.0)
        self.next_breath_state(None, None)

    def update_timer(self, dt):
        if self.time_remaining <= 0:
            self.end_session(interrupted=False)
            return
            
        self.time_remaining -= 1
        mins, secs = divmod(self.time_remaining, 60)
        self.timer_label.text = f"{mins}:{secs:02d}"

    def next_breath_state(self, widget, animation):
        if not self.is_active:
            return

        timings = self.get_current_timings()
        
        if self.current_state == 0:
            self._execute_state("INHALE", timings[0], target_size=dp(230))
        elif self.current_state == 1:
            self._execute_state("HOLD", timings[1], target_size=dp(230))
        elif self.current_state == 2:
            self._execute_state("EXHALE", timings[2], target_size=dp(50))
        elif self.current_state == 3:
            self._execute_state("HOLD", timings[3], target_size=dp(50))

        self.current_state = (self.current_state + 1) % 4

    def _execute_state(self, instruction, duration, target_size):
        if duration == 0:
            Clock.schedule_once(lambda dt: self.next_breath_state(None, None), 0)
            return

        trigger_haptic_feedback(0.05)
        self.instruction_label.text = instruction
        
        circle = self.dynamic_circle
        center_x = self.breathing_area.width / 2
        center_y = self.breathing_area.height / 2
        new_pos = (center_x - target_size / 2, center_y - target_size / 2)

        self.current_anim = Animation(size=(target_size, target_size), pos=new_pos, duration=duration)
        self.current_anim.bind(on_complete=self.next_breath_state)
        self.current_anim.start(circle)

    def end_session(self, interrupted=False):
        self.is_active = False
        if self.timer_event:
            self.timer_event.cancel()
        if self.current_anim:
            self.current_anim.cancel(self.dynamic_circle)

        self.current_state = 0
        self.instruction_label.text = "SESSION INTERRUPTED" if interrupted else "SESSION COMPLETE"
        trigger_haptic_feedback(0.05)
        
        # Reset Action Button back to GREEN "START SESSION"
        self.play_btn.text = "START SESSION"
        self.play_btn.background_color = (0.1, 0.6, 0.3, 1)

        # Unlock carousel controls & custom adjusters
        self.selector_layout.disabled = False
        self.update_exercise_ui()
        
        # Reset expanding circle back to idle baseline size
        circle = self.dynamic_circle
        center_x = self.breathing_area.width / 2
        center_y = self.breathing_area.height / 2
        idle_size = dp(50)
        Animation(size=(idle_size, idle_size), pos=(center_x - idle_size / 2, center_y - idle_size / 2), duration=0.5).start(circle)

    def on_leave(self):
        self.end_session(interrupted=True)
        
class ScreenshotScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_started = False
        self.shapes_data = []
        self.target_shapes = []
        self.target_zoom = 1.0
        self.target_x = 0.0
        self.target_y = 0.0
        
        self.frame_size = Window.width  
        self.target_frame_size = dp(90)

        # --- BACKGROUND ---
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)  # Deep Cosmic Background
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        
        self.bind(pos=self._update_screen_size, size=self._update_screen_size)

        self.main_layout = FloatLayout()
        self.add_widget(self.main_layout)

        # --- BACK BUTTON ---
        self.back_btn = Button(
            text="< MENU",
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size=Scale.font(15),
            size_hint=(0.25, 0.05),
            pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='',
            background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self._go_back)
        self.main_layout.add_widget(self.back_btn)

        # --- TARGET FRAME (Above main map) ---
        self.target_container = RelativeLayout(
            size_hint=(None, None),
            size=(self.target_frame_size, self.target_frame_size),
            pos_hint={'center_x': 0.5, 'top': 0.93}
        )
        
        with self.target_container.canvas.before:
            Color(0.15, 0.15, 0.25, 1)
            self.target_bg = Rectangle(pos=(0, 0), size=self.target_container.size)
            Color(1, 1, 1, 1)
            self.target_border = Line(rectangle=(0, 0, self.target_frame_size, self.target_frame_size), width=dp(2))

        self.target_stencil = StencilView(size_hint=(None, None), size=(self.target_frame_size, self.target_frame_size))
        self.target_map_widget = Widget(size_hint=(None, None), size=(self.target_frame_size, self.target_frame_size))
        
        self.target_stencil.add_widget(self.target_map_widget)
        self.target_container.add_widget(self.target_stencil)
        self.main_layout.add_widget(self.target_container)

        # --- MAIN YELLOW FRAME ---
        self.yellow_frame = RelativeLayout(
            size_hint=(None, None),
            size=(self.frame_size, self.frame_size),
            pos_hint={'center_x': 0.5, 'top': 0.78}
        )
        
        with self.yellow_frame.canvas.before:
            Color(1, 1, 0, 1)  # Yellow
            self.frame_border = Line(rectangle=(0, 0, self.frame_size, self.frame_size), width=dp(2))

        self.main_stencil = StencilView(size_hint=(None, None), size=(self.frame_size, self.frame_size))
        self.main_scatter = Scatter(do_rotation=False, size_hint=(None, None), size=(self.frame_size, self.frame_size))
        self.map_widget = Widget(size_hint=(None, None), size=(self.frame_size, self.frame_size))
        
        self.main_scatter.add_widget(self.map_widget)
        self.main_stencil.add_widget(self.main_scatter)
        self.yellow_frame.add_widget(self.main_stencil)

        # Dynamic clip check on transform
        self.main_scatter.bind(transform=self.on_scatter_transform)

        # --- FLASH OVERLAY ---
        self.flash_overlay = Widget(size_hint=(None, None), size=(self.frame_size, self.frame_size), opacity=0)
        with self.flash_overlay.canvas:
            Color(1, 1, 1, 1)
            self.flash_rect = Rectangle(pos=(0, 0), size=(self.frame_size, self.frame_size))
        self.yellow_frame.add_widget(self.flash_overlay)
        
        self.main_layout.add_widget(self.yellow_frame)

        # --- ACTION ROW (Camera + Instructions Button) ---
        self.action_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint=(0.4, 0.07),
            pos_hint={'center_x': 0.5, 'top': 0.21}
        )
        
        self.camera_btn = Button(
            text="[O]", 
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size='18sp',
            size_hint_x=0.75,
            background_normal='',
            background_color=(1, 1, 0, 1),
            color=(0, 0, 0, 1)
        )
        self.camera_btn.bind(on_release=self.take_screenshot)
        self.action_row.add_widget(self.camera_btn)

        self.help_btn = Button(
            text="?",
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size='16sp',
            size_hint_x=0.25,
            background_normal='',
            background_color=(0, 0.5, 0.8, 1),
            color=(1, 1, 1, 1)
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.action_row.add_widget(self.help_btn)

        self.main_layout.add_widget(self.action_row)

        # --- FEEDBACK UI ---
        self.feedback_layout = BoxLayout(
            orientation='vertical',
            size_hint=(1, 0.12),
            pos_hint={'center_x': 0.5, 'top': 0.13},
            spacing=dp(5)
        )
        self.feedback_label = Label(
            text="",
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size='11sp',
            color=(1, 1, 1, 1),
            halign='center'
        )
        self.next_btn = Button(
            text="NEXT TARGET",
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size='11sp',
            size_hint=(0.6, None),
            height=dp(35),
            pos_hint={'center_x': 0.5},
            background_normal='',
            background_color=(0.1, 0.6, 0.3, 1),
            opacity=0,
            disabled=True
        )
        self.next_btn.bind(on_release=self.start_round)
        
        self.feedback_layout.add_widget(self.feedback_label)
        self.feedback_layout.add_widget(self.next_btn)
        self.main_layout.add_widget(self.feedback_layout)

    # --- INSTRUCTION OVERLAY LOGIC ---
    def show_instructions_overlay(self, instance):
        self.action_row.disabled = True
        self.back_btn.disabled = True
        
        game_name = "Screenshot"
        rules = [
            "Pinch or drag across the yellow map frame to pan and zoom",
            "Align your camera frame to match the miniature target image above",
            "Tap the shutter button [O] when you have framed the target section"
        ]
        
        overlay = InstructionOverlay(
            game_name=game_name,
            rules_list=rules,
            close_callback=self.on_instructions_closed
        )
        self.main_layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.action_row.disabled = False
        self.back_btn.disabled = False

    def on_leave(self, *args):
        # Clean up instruction overlay if leaving screen early
        for child in list(self.main_layout.children):
            if isinstance(child, InstructionOverlay):
                self.main_layout.remove_widget(child)

    # --- UI SYNCHRONIZATION ---
    def _update_screen_size(self, instance, *args):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size
        
        new_width = instance.width
        if new_width > 10 and self.frame_size != new_width:
            self.frame_size = new_width
            
            self.yellow_frame.size = (new_width, new_width)
            self.frame_border.rectangle = (0, 0, new_width, new_width)
            
            self.main_stencil.size = (new_width, new_width)
            self.main_scatter.size = (new_width, new_width)
            self.map_widget.size = (new_width, new_width)
            
            self.flash_overlay.size = (new_width, new_width)
            self.flash_rect.size = (new_width, new_width)
            
            if self.game_started:
                self.draw_main_shapes()

        if not self.game_started and new_width > 10:
            self.game_started = True
            Clock.schedule_once(self.start_round, 0.1)

    def _go_back(self, instance):
        self.manager.current = 'menu'

    def on_scatter_transform(self, instance, value):
        if self.game_started:
            self.draw_main_shapes()

    # --- GAME LOGIC ---
    def trigger_haptic_buzz(self):
        app = App.get_running_app()
        haptics_enabled = getattr(app, 'haptics_enabled', True)
        if haptics_enabled and vibrator is not None:
            try:
                vibrator.vibrate(time=0.05)
            except NotImplementedError:
                pass

    def start_round(self, *args):
        self.feedback_label.text = ""
        self.next_btn.opacity = 0
        self.next_btn.disabled = True
        
        # 1. Generate 100 Pastel Galaxy Shapes
        self.shapes_data = []
        for _ in range(100):
            self.shapes_data.append({
                'r': random.uniform(0.6, 1.0),
                'g': random.uniform(0.6, 1.0),
                'b': random.uniform(0.6, 1.0),
                'x_norm': random.uniform(0.0, 1.0),
                'y_norm': random.uniform(0.0, 1.0),
                'size_norm': random.uniform(0.02, 0.08)
            })

        self.main_scatter.scale = 1.0
        self.main_scatter.pos = (0, 0)
        self.draw_main_shapes()

        # 2. Find target zone with 8 to 12 shapes
        max_attempts = 150
        for _ in range(max_attempts):
            zoom = random.uniform(1.5, 3.0)
            vis_w = 1.0 / zoom  
            tx = random.uniform(0, 1.0 - vis_w)
            ty = random.uniform(0, 1.0 - vis_w)

            candidate_shapes = []
            for s in self.shapes_data:
                rel_x = (s['x_norm'] - tx) * zoom
                rel_y = (s['y_norm'] - ty) * zoom
                rel_size = s['size_norm'] * zoom

                if (0 <= rel_x and rel_x + rel_size <= 1.0 and
                    0 <= rel_y and rel_y + rel_size <= 1.0):
                    candidate_shapes.append(s)

            if 8 <= len(candidate_shapes) <= 12:
                self.target_zoom = zoom
                self.target_x = tx
                self.target_y = ty
                self.target_shapes = candidate_shapes
                break
        else:
            self.target_zoom = 2.0
            self.target_x = 0.25
            self.target_y = 0.25
            self.target_shapes = [
                s for s in self.shapes_data 
                if 0.25 <= s['x_norm'] <= 0.75 and 0.25 <= s['y_norm'] <= 0.75
            ][:10]

        self.draw_target_shapes()

    def draw_main_shapes(self):
        self.map_widget.canvas.clear()
        W = self.frame_size
        if W <= 0: 
            return

        scale = self.main_scatter.scale
        sx = self.main_scatter.x
        sy = self.main_scatter.y

        # Compute bounding rectangle for current camera view
        min_x = -sx / scale
        max_x = (W - sx) / scale
        min_y = -sy / scale
        max_y = (W - sy) / scale

        with self.map_widget.canvas:
            StencilPush()
            Rectangle(pos=(0, 0), size=(W, W))
            StencilUse()

            for s in self.shapes_data:
                diameter = s['size_norm'] * W
                px = s['x_norm'] * W
                py = s['y_norm'] * W

                if (px >= min_x and (px + diameter) <= max_x and
                    py >= min_y and (py + diameter) <= max_y):
                    Color(s['r'], s['g'], s['b'], 1.0)
                    Ellipse(pos=(px, py), size=(diameter, diameter))

            StencilUnUse()
            Rectangle(pos=(0, 0), size=(W, W))
            StencilPop()

    def draw_target_shapes(self):
        self.target_map_widget.canvas.clear()
        TW = self.target_frame_size
        if TW <= 0: 
            return

        with self.target_map_widget.canvas:
            for s in self.target_shapes:
                rel_x = (s['x_norm'] - self.target_x) * self.target_zoom
                rel_y = (s['y_norm'] - self.target_y) * self.target_zoom
                rel_size = s['size_norm'] * self.target_zoom

                diameter = rel_size * TW
                px = rel_x * TW
                py = rel_y * TW

                if px >= 0 and (px + diameter) <= TW and py >= 0 and (py + diameter) <= TW:
                    Color(s['r'], s['g'], s['b'], 1.0)
                    Ellipse(pos=(px, py), size=(diameter, diameter))

    def take_screenshot(self, instance):
        # White Flash Effect
        self.flash_overlay.opacity = 0.8
        anim = Animation(opacity=0, duration=0.25)
        anim.start(self.flash_overlay)

        W = self.frame_size
        if W <= 0: 
            return

        scale = self.main_scatter.scale
        sx = self.main_scatter.x
        sy = self.main_scatter.y
        
        vis_x = -sx / (W * scale)
        vis_y = -sy / (W * scale)

        err_scale = abs(scale - self.target_zoom) / self.target_zoom
        err_x = abs(vis_x - self.target_x)
        err_y = abs(vis_y - self.target_y)

        if err_scale <= 0.15 and err_x <= 0.10 and err_y <= 0.10:
            self.trigger_haptic_buzz()
            self.feedback_label.text = "PERFECT ALIGNMENT!"
            self.feedback_label.color = (0.47, 0.87, 0.47, 1)
            self.next_btn.opacity = 1
            self.next_btn.disabled = False
            self.camera_btn.disabled = True
            Clock.schedule_once(lambda dt: setattr(self.camera_btn, 'disabled', False), 1.0)
        else:
            self.feedback_label.text = "NOT QUITE. ADJUST AND TRY AGAIN."
            self.feedback_label.color = (0.87, 0.47, 0.47, 1)
            
class LineFillScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_started = False
        self.grid_rows = 4
        self.grid_cols = 4
        self.active_cells = set()  # (r, c) tuples that belong to the shape
        self.path = []             # Ordered list of (r, c) touched cells
        self.is_drawing = False
        self.level_number = 1
        
        self.grid_size = dp(280)
        self.cell_size = 0

        # --- BACKGROUND ---
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)  # Deep Cosmic Background
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.main_layout = FloatLayout()
        self.add_widget(self.main_layout)

        # --- BACK BUTTON ---
        self.back_btn = Button(
            text="< MENU",
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size=Scale.font(15),
            size_hint=(0.25, 0.05),
            pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='',
            background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self._go_back)
        self.main_layout.add_widget(self.back_btn)

        # --- HEADER / LEVEL TITLE ---
        self.title_label = Label(
            text="SHAPE FILL",
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size=Scale.font(30),
            color=(0.47, 0.87, 0.47, 1),
            pos_hint={'center_x': 0.5, 'top': 0.93},
            size_hint=(1, 0.08)
        )
        self.main_layout.add_widget(self.title_label)

        # --- GRID CONTAINER ---
        self.grid_container = RelativeLayout(
            size_hint=(None, None),
            size=(self.grid_size, self.grid_size),
            pos_hint={'center_x': 0.5, 'center_y': 0.52}
        )
        
        # Grid canvas layers
        self.grid_bg_widget = Widget(size_hint=(1, 1))
        self.drawing_widget = Widget(size_hint=(1, 1))
        self.grid_container.add_widget(self.grid_bg_widget)
        self.grid_container.add_widget(self.drawing_widget)
        
        self.main_layout.add_widget(self.grid_container)

        # --- ACTION ROW (Skip + Help / Instructions Buttons) ---
        self.action_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint=(0.8, 0.07),
            pos_hint={'center_x': 0.5, 'top': 0.20}
        )

        self.skip_btn = Button(
            text="SKIP",
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size='12sp',
            size_hint=(0.75, 1),
            background_normal='',
            background_color=(0.3, 0.3, 0.4, 1),
            color=(1, 1, 1, 1)
        )
        self.skip_btn.bind(on_release=self.skip_shape)

        self.help_btn = Button(
            text="?",
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size='16sp',
            size_hint=(0.25, 1),
            background_normal='',
            background_color=(0, 0.5, 0.8, 1),
            color=(1, 1, 1, 1)
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)

        self.action_row.add_widget(self.skip_btn)
        self.action_row.add_widget(self.help_btn)
        self.main_layout.add_widget(self.action_row)

        # --- FEEDBACK & NEXT BUTTON ---
        self.feedback_layout = BoxLayout(
            orientation='vertical',
            size_hint=(1, 0.12),
            pos_hint={'center_x': 0.5, 'top': 0.12},
            spacing=dp(5)
        )
        self.feedback_label = Label(
            text="",
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size='11sp',
            color=(1, 1, 1, 1),
            halign='center'
        )
        self.next_btn = Button(
            text="NEXT SHAPE",
            font_name="assets/fonts/ARCADE_N.TTF",
            font_size='11sp',
            size_hint=(0.6, None),
            height=dp(35),
            pos_hint={'center_x': 0.5},
            background_normal='',
            background_color=(0.1, 0.6, 0.3, 1),
            opacity=0,
            disabled=True
        )
        self.next_btn.bind(on_release=self.next_level)

        self.feedback_layout.add_widget(self.feedback_label)
        self.feedback_layout.add_widget(self.next_btn)
        self.main_layout.add_widget(self.feedback_layout)

    # --- SCREEN LIFECYCLE ---
    def on_enter(self, *args):
        if not self.game_started:
            self.game_started = True
            Clock.schedule_once(self.start_round, 0.1)

    def on_leave(self, *args):
        for child in list(self.main_layout.children):
            if isinstance(child, InstructionOverlay):
                self.main_layout.remove_widget(child)

    def _update_bg(self, instance, *args):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def _go_back(self, instance):
        self.manager.current = 'menu'

    # --- INSTRUCTIONS OVERLAY ---
    def show_instructions_overlay(self, instance):
        self.action_row.disabled = True
        self.back_btn.disabled = True
        
        game_name = "Shape Fill"
        rules = [
            "Tap and hold any grid tile to spawn your starting green dot",
            "Drag your finger through adjacent tiles to connect them with a path",
            "Cover every tile without backtracking or crossing over existing lines",
            "Fill all tiles to complete the shape!"
        ]
        
        overlay = InstructionOverlay(
            game_name=game_name,
            rules_list=rules,
            close_callback=self.on_instructions_closed
        )
        self.main_layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.action_row.disabled = False
        self.back_btn.disabled = False

    # --- LEVEL & GRID GENERATION ---
    def start_round(self, *args):
        self.feedback_label.text = "FILL THE SHAPE"
        self.feedback_label.color = (1, 1, 1, 1)
        self.next_btn.opacity = 0
        self.next_btn.disabled = True
        self.skip_btn.disabled = False
        self.path = []
        self.is_drawing = False

        if self.level_number <= 3:
            self.grid_rows, self.grid_cols = 3, 3
        elif self.level_number <= 7:
            self.grid_rows, self.grid_cols = 4, 4
        else:
            self.grid_rows, self.grid_cols = 5, 5

        self.cell_size = self.grid_size / max(self.grid_rows, self.grid_cols)

        self.generate_solvable_grid()
        self.draw_grid_background()
        self.drawing_widget.canvas.clear()

    def skip_shape(self, instance):
        """Generates a new target shape without resetting level progress."""
        trigger_haptic_feedback(0.04)
        self.start_round()

    def generate_solvable_grid(self):
        """Generates a connected set of cells using a random walk."""
        self.active_cells = set()
        total_cells_target = int(self.grid_rows * self.grid_cols * random.uniform(0.7, 0.9))
        
        curr = (random.randint(0, self.grid_rows - 1), random.randint(0, self.grid_cols - 1))
        self.active_cells.add(curr)
        
        while len(self.active_cells) < total_cells_target:
            r, c = curr
            neighbors = []
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.grid_rows and 0 <= nc < self.grid_cols:
                    neighbors.append((nr, nc))
            
            curr = random.choice(neighbors)
            self.active_cells.add(curr)

    def draw_grid_background(self):
        self.grid_bg_widget.canvas.clear()
        cs = self.cell_size
        
        with self.grid_bg_widget.canvas:
            for (r, c) in self.active_cells:
                x = c * cs + dp(4)
                y = r * cs + dp(4)
                w = cs - dp(8)
                
                Color(0.12, 0.16, 0.32, 0.8)
                Rectangle(pos=(x, y), size=(w, w))
                
                Color(0.2, 0.4, 0.6, 0.5)
                Line(rectangle=(x, y, w, w), width=dp(1.2))

    # --- TOUCH & DRAG LOGIC ---
    def get_cell_from_pos(self, local_pos):
        x, y = local_pos
        cs = self.cell_size
        col = int(x // cs)
        row = int(y // cs)
        
        if 0 <= row < self.grid_rows and 0 <= col < self.grid_cols:
            if (row, col) in self.active_cells:
                return (row, col)
        return None

    def on_touch_down(self, touch):
        if not self.game_started or self.next_btn.opacity > 0:
            return super().on_touch_down(touch)

        local_pos = self.grid_container.to_widget(*touch.pos)
        cell = self.get_cell_from_pos(local_pos)

        if cell:
            self.is_drawing = True
            self.path = [cell]
            self.redraw_path()
            trigger_haptic_feedback(0.04)
            return True
            
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if not self.is_drawing:
            return super().on_touch_move(touch)

        local_pos = self.grid_container.to_widget(*touch.pos)
        cell = self.get_cell_from_pos(local_pos)

        if cell and cell != self.path[-1]:
            last_cell = self.path[-1]
            
            is_adjacent = (abs(cell[0] - last_cell[0]) + abs(cell[1] - last_cell[1])) == 1

            if is_adjacent:
                if cell in self.path:
                    self.trigger_fault("DON'T CROSS PATHS!")
                else:
                    self.path.append(cell)
                    self.redraw_path()
                    trigger_haptic_feedback(0.02)
            else:
                if cell in self.path:
                    self.trigger_fault("DON'T CROSS PATHS!")

        return True

    def on_touch_up(self, touch):
        if self.is_drawing:
            self.is_drawing = False
            
            if len(self.path) == len(self.active_cells):
                self.trigger_victory()
            else:
                self.trigger_fault("FILL EVERY TILE!")
            return True
            
        return super().on_touch_up(touch)

    # --- RENDERING & FEEDBACK ---
    def redraw_path(self, alpha=1.0):
        self.drawing_widget.canvas.clear()
        if not self.path:
            return

        cs = self.cell_size
        line_points = []

        with self.drawing_widget.canvas:
            Color(0.47, 0.87, 0.47, alpha)  # Pastel Green

            start_r, start_c = self.path[0]
            dot_r = cs * 0.25
            dot_x = start_c * cs + (cs / 2) - dot_r
            dot_y = start_r * cs + (cs / 2) - dot_r
            Ellipse(pos=(dot_x, dot_y), size=(dot_r * 2, dot_r * 2))

            for (r, c) in self.path:
                cx = c * cs + (cs / 2)
                cy = r * cs + (cs / 2)
                line_points.extend([cx, cy])

            if len(line_points) >= 4:
                Line(points=line_points, width=dp(10), joint='round', cap='round')

    def trigger_fault(self, message):
        self.is_drawing = False
        trigger_haptic_feedback(0.08)
        self.feedback_label.text = message
        self.feedback_label.color = (0.87, 0.47, 0.47, 1)  # Pastel Red

        anim = Animation(opacity=0, duration=0.35)
        anim.bind(on_complete=self._clear_failed_path)
        anim.start(self.drawing_widget)

    def _clear_failed_path(self, *args):
        self.path = []
        self.drawing_widget.canvas.clear()
        self.drawing_widget.opacity = 1.0

    def trigger_victory(self):
        trigger_haptic_feedback(0.12)
        self.feedback_label.text = "PERFECT SHAPE!"
        self.feedback_label.color = (0.47, 0.87, 0.47, 1)  # Pastel Green

        self.skip_btn.disabled = True
        self.next_btn.opacity = 1
        self.next_btn.disabled = False

    def next_level(self, instance):
        self.level_number += 1
        self.start_round()
        
class MathInvadersScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_active = False
        self.score = 0
        self.high_score = 0
        self.saucers = []  # List of dicts: {'widget': RelativeLayout, 'x': float, 'y': float, 'expr': str, 'answer': int}
        self.current_input = ""
        self.spawn_timer = 0.0
        self.spawn_interval = 3.0
        self.fall_speed = dp(35)
        self.game_event = None

        self.rover_x = Window.width / 2

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        # --- BACKGROUND ---
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)  # Deep Cosmic Background
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.load_high_score()

        # --- HUD HEADER ---
        self.title_label = Label(
            text="SPACE MATH",
            font_size='16sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.95}
        )
        self.layout.add_widget(self.title_label)

        self.score_label = Label(
            text="SCORE: 0",
            font_size='11sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.3, 'center_y': 0.90}
        )
        self.layout.add_widget(self.score_label)

        self.hi_score_label = Label(
            text=f"BEST: {self.high_score}",
            font_size='11sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.7, 'center_y': 0.90}
        )
        self.layout.add_widget(self.hi_score_label)

        self.input_display = Label(
            text="INPUT: _",
            font_size='14sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 0.84, 0, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.84}
        )
        self.layout.add_widget(self.input_display)

        # --- BACK BUTTON ---
        self.back_btn = Button(
            text="< MENU",
            font_size=Scale.font(15),
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05),
            pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='',
            background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        # --- PLAY FIELD CONTAINER FOR SAUCERS ---
        self.play_area = RelativeLayout(size_hint=(1, 1))
        self.layout.add_widget(self.play_area)

        # --- GUN ROVER WIDGET ---
        self.rover_widget = Widget(size_hint=(1, 1))
        self.layout.add_widget(self.rover_widget)

        # --- 25% OPACITY NUMPAD OVERLAY ---
        self.numpad_container = RelativeLayout(
            size_hint=(0.85, 0.32),
            pos_hint={'center_x': 0.5, 'y': 0.02}
        )
        
        with self.numpad_container.canvas.before:
            Color(0.08, 0.12, 0.28, 0.25)  # 25% semi-transparent overlay
            self.numpad_bg = Rectangle(pos=(0, 0), size=self.numpad_container.size)
            Color(0, 0.75, 1, 0.25)
            self.numpad_border = Line(rectangle=(0, 0, Window.width * 0.85, Window.height * 0.32), width=dp(1.5))

        self.numpad_container.bind(size=self._sync_numpad_bg, pos=self._sync_numpad_bg)

        self.numpad_grid = GridLayout(
            cols=3,
            rows=4,
            spacing=dp(4),
            padding=dp(6),
            size_hint=(1, 1)
        )
        self.build_numpad_buttons()
        self.numpad_container.add_widget(self.numpad_grid)
        self.layout.add_widget(self.numpad_container)

        # --- ACTION ROW ---
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint=(0.9, 0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME",
            font_size=Scale.font(25),
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1),
            size_hint_x=0.8,
            background_normal='',
            background_color=(0, 0.75, 1, 1)
        )
        self.start_btn.bind(on_release=self.start_game)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?",
            font_size='16sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='',
            background_color=(0, 0.5, 0.8, 1),
            color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

    # --- NUMPAD BUILDER (25% Opacity Backgrounds) ---
    def build_numpad_buttons(self):
        keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'CLR', '0', 'FIRE']
        for key in keys:
            if key == 'CLR':
                bg_col = (0.6, 0.2, 0.2, 0.25)
            elif key == 'FIRE':
                bg_col = (0.1, 0.6, 0.3, 0.25)
            else:
                bg_col = (0.12, 0.18, 0.38, 0.25)

            btn = Button(
                text=key,
                font_name='assets/fonts/ARCADE_N.TTF',
                font_size='14sp',
                background_normal='',
                background_color=bg_col,
                color=(1, 1, 1, 0.85)
            )
            btn.bind(on_release=self.handle_numpad_press)
            self.numpad_grid.add_widget(btn)

    def _sync_numpad_bg(self, instance, value):
        self.numpad_bg.size = instance.size
        self.numpad_border.rectangle = (0, 0, instance.width, instance.height)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    # --- INSTRUCTIONS OVERLAY ---
    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Space Math"
        rules = [
            "Alien flying saucers containing math problems descend from above",
            "Type the correct answer on the semi-transparent numpad and tap FIRE",
            "Your green gun rover will align and blast targeted saucers",
            "If any flying saucer touches the bottom boundary, the aliens invade!"
        ]
        overlay = InstructionOverlay(
            game_name=game_name,
            rules_list=rules,
            close_callback=self.on_instructions_closed
        )
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    # --- LIFECYCLE HANDLERS ---
    def on_pre_enter(self, *args):
        self.stop_game_engine()
        self.title_label.text = "SPACE MATH"
        self.title_label.color = (0, 0.75, 1, 1)
        self.input_display.text = "INPUT: _"
        self.score_label.text = "SCORE: 0"
        self.load_high_score()
        self.hi_score_label.text = f"BEST: {self.high_score}"
        if self.play_help_row not in self.layout.children:
            self.layout.add_widget(self.play_help_row)
        self.play_help_row.disabled = False
        self.rover_x = Window.width / 2
        self.draw_rover()

    def on_leave(self, *args):
        self.stop_game_engine()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def go_back_to_menu(self, instance):
        self.stop_game_engine()
        self.manager.current = 'menu'

    # --- PERSISTENCE ---
    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('space_math_high', 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['space_math_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    # --- ROVER GRAPHICS ---
    def draw_rover(self):
        self.rover_widget.canvas.clear()
        with self.rover_widget.canvas:
            Color(0.47, 0.87, 0.47, 1)  # Retro Pastel Green
            cx = self.rover_x
            cy = dp(5)
            w = dp(30)
            h = dp(25)

            v = [
                cx, cy + h, 0, 0,
                cx - w / 2, cy, 0, 0,
                cx + w / 2, cy, 0, 0
            ]
            Mesh(vertices=v, indices=[0, 1, 2], mode='triangles')

    # --- GAME ENGINE & LOOP ---
    def start_game(self, instance):
        if self.play_help_row in self.layout.children:
            self.layout.remove_widget(self.play_help_row)

        self.clear_saucers()
        self.score = 0
        self.current_input = ""
        self.spawn_timer = 0.0
        self.spawn_interval = 2.8
        self.fall_speed = dp(35)
        self.rover_x = Window.width / 2
        self.draw_rover()

        self.score_label.text = f"SCORE: {self.score}"
        self.input_display.text = "INPUT: _"
        self.title_label.text = "DEFEND EARTH!"
        self.title_label.color = (0, 0.75, 1, 1)

        self.game_active = True
        self.spawn_saucer()

        if self.game_event:
            Clock.unschedule(self.game_event)
        self.game_event = Clock.schedule_interval(self.game_loop_tick, 1.0 / 60.0)

    def generate_short_expression(self):
        existing_answers = [s['answer'] for s in self.saucers]

        for _ in range(30):
            op = random.choice(['+', '-', 'x', '/'])
            if op == '+':
                a = random.randint(1, 15)
                b = random.randint(1, 15)
                ans = a + b
            elif op == '-':
                a = random.randint(2, 20)
                b = random.randint(1, a)
                ans = a - b
            elif op == 'x':
                a = random.randint(1, 9)
                b = random.randint(1, 9)
                ans = a * b
            else:  # '/'
                b = random.randint(1, 10)
                ans = random.randint(1, 8)
                a = b * ans

            if ans not in existing_answers:
                formatted_expr = f"{a: >3}\n{op}{b: >2}"
                return formatted_expr, ans

        a, b = random.randint(1, 5), random.randint(1, 5)
        return f"{a: >3}\n+{b: >2}", a + b

    def spawn_saucer(self):
        if not self.game_active:
            return

        expr_str, ans = self.generate_short_expression()
        diameter = dp(50)
        min_x = dp(10)
        max_x = Window.width - diameter - dp(10)
        pos_x = random.uniform(min_x, max_x)
        pos_y = Window.height * 0.80

        # RelativeLayout ensures local canvas pos=(0, 0) moves cleanly with layout.pos
        saucer_layout = RelativeLayout(
            size_hint=(None, None),
            size=(diameter, diameter),
            pos=(pos_x, pos_y)
        )

        with saucer_layout.canvas.before:
            Color(1, 0.9, 0.2, 1)  # Solid Yellow Fill
            Ellipse(pos=(0, 0), size=(diameter, diameter))

        lbl = Label(
            text=expr_str,
            font_name='assets/fonts/ARCADE_N.TTF',
            font_size='11sp',
            color=(0, 0, 0, 1),  # Black text inside yellow circle
            halign='center',
            valign='middle',
            size_hint=(1, 1),
            pos=(0, 0)
        )
        lbl.bind(size=lbl.setter('text_size'))
        saucer_layout.add_widget(lbl)

        self.play_area.add_widget(saucer_layout)

        self.saucers.append({
            'widget': saucer_layout,
            'x': pos_x,
            'y': pos_y,
            'expr': expr_str,
            'answer': ans,
            'diameter': diameter
        })

    def game_loop_tick(self, dt):
        if not self.game_active:
            return

        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            if len(self.saucers) < 6:
                self.spawn_saucer()

        danger_line_y = 0.0
        current_speed = self.fall_speed + (self.score * dp(0.8))

        for s in self.saucers[:]:
            s['y'] -= current_speed * dt
            s['widget'].pos = (s['x'], s['y'])

            # Game Over: Touches the bottom of the screen
            if s['y'] <= danger_line_y:
                self.trigger_game_over()
                return

    # --- NUMPAD & FIRE LOGIC ---
    def handle_numpad_press(self, instance):
        if not self.game_active:
            return

        val = instance.text
        if val == 'CLR':
            self.current_input = ""
        elif val == 'FIRE':
            self.evaluate_submission()
        else:
            if len(self.current_input) < 4:
                self.current_input += val

        self.input_display.text = f"INPUT: {self.current_input if self.current_input else '_'}"

    def evaluate_submission(self):
        if not self.current_input or not self.game_active:
            return

        try:
            target_val = int(self.current_input)
        except ValueError:
            self.current_input = ""
            self.input_display.text = "INPUT: _"
            return

        matched_saucers = [s for s in self.saucers if s['answer'] == target_val]

        if matched_saucers:
            trigger_haptic_feedback(0.08)

            # Target Rover to the X center of the most recent destroyed saucer
            latest_saucer = matched_saucers[-1]
            self.rover_x = latest_saucer['x'] + (latest_saucer['diameter'] / 2)
            self.draw_rover()

            for s in matched_saucers:
                self.play_area.remove_widget(s['widget'])
                self.saucers.remove(s)
                self.score += 1

            self.score_label.text = f"SCORE: {self.score}"
            if self.score > self.high_score:
                self.high_score = self.score
                self.hi_score_label.text = f"BEST: {self.high_score}"
                self.save_high_score()

            self.spawn_interval = max(1.2, 2.8 - (self.score * 0.05))
        else:
            trigger_haptic_feedback(0.04)

        self.current_input = ""
        self.input_display.text = "INPUT: _"

    # --- GAME OVER & CLEANUP ---
    def trigger_game_over(self):
        self.stop_game_engine()
        trigger_haptic_feedback(0.12)
        self.title_label.text = "ALIENS INVADED!"
        self.title_label.color = (0.9, 0.2, 0.2, 1)
        self.start_btn.text = "RETRY DEFENSE"

        if self.play_help_row not in self.layout.children:
            self.layout.add_widget(self.play_help_row)

    def clear_saucers(self):
        for s in self.saucers:
            self.play_area.remove_widget(s['widget'])
        self.saucers = []

    def stop_game_engine(self):
        self.game_active = False
        if self.game_event:
            Clock.unschedule(self.game_event)
            self.game_event = None
        self.clear_saucers()
        self.current_input = ""
        
class SequenceSwitchScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_active = False
        self.round_number = 1
        self.score = 0
        self.high_score = 0

        self.full_sequence = []      # Expected 6-number sequence
        self.target_indices = []     # Indices of hidden numbers
        self.board_state = []        # Current values on the 6 board slots (int or None)
        self.inventory_pool = []     # Numbers available in the tile bank
        self.selected_slot_idx = None  # Currently highlighted board slot

        self.board_buttons = []
        self.inventory_buttons = []

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        # --- BACKGROUND ---
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)  # Deep Cosmic Background (#0A0F2C)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.load_high_score()

        # --- HUD HEADER ---
        self.title_label = Label(
            text="SEQUENCE SWITCH",
            font_size='16sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.94}
        )
        self.layout.add_widget(self.title_label)

        self.score_label = Label(
            text="SCORE: 0",
            font_size='11sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.3, 'center_y': 0.88}
        )
        self.layout.add_widget(self.score_label)

        self.hi_score_label = Label(
            text=f"BEST: {self.high_score}",
            font_size='11sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.7, 'center_y': 0.88}
        )
        self.layout.add_widget(self.hi_score_label)

        self.status_label = Label(
            text="FILL IN THE PATTERN",
            font_size='10sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 0.84, 0, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.82}
        )
        self.layout.add_widget(self.status_label)

        # --- BACK BUTTON ---
        self.back_btn = Button(
            text="< MENU",
            font_size=Scale.font(15),
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05),
            pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='',
            background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        # --- SEQUENCE BOARD CONTAINER (6 Horizontal Slots) ---
        self.board_container = GridLayout(
            cols=3,
            rows=2,
            spacing=dp(8),
            size_hint=(0.90, 0.26),
            pos_hint={'center_x': 0.5, 'center_y': 0.60}
        )
        self.layout.add_widget(self.board_container)

        # --- INVENTORY TILE BANK CONTAINER (Grid of Options) ---
        self.bank_label = Label(
            text="TILE BANK",
            font_size='10sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 0.8),
            pos_hint={'center_x': 0.5, 'center_y': 0.42}
        )
        self.layout.add_widget(self.bank_label)

        self.bank_container = GridLayout(
            cols=4,
            rows=2,
            spacing=dp(8),
            size_hint=(0.90, 0.20),
            pos_hint={'center_x': 0.5, 'center_y': 0.30}
        )
        self.layout.add_widget(self.bank_container)

        # --- ACTION ROW (Submit / Start + Help Button) ---
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint=(0.9, 0.09),
            pos_hint={'center_x': 0.5, 'center_y': 0.12}
        )
        self.layout.add_widget(self.play_help_row)

        self.action_btn = Button(
            text="START GAME",
            font_size=Scale.font(25),
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1),
            size_hint_x=0.8,
            background_normal='',
            background_color=(0, 0.75, 1, 1)
        )
        self.action_btn.bind(on_release=self.handle_action_press)
        self.play_help_row.add_widget(self.action_btn)

        self.help_btn = Button(
            text="?",
            font_size='16sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='',
            background_color=(0, 0.5, 0.8, 1),
            color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

    # --- INSTRUCTIONS OVERLAY ---
    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        game_name = "Sequence Switch"
        rules = [
            "Examine the sequence pattern displayed on the board slots",
            "Tap an open slot [ ? ] to highlight it, then tap a number from your tile bank",
            "Tapping any number in the bank automatically places it in the next open slot",
            "Tap a filled tile on the board to return it to your bank",
            "Tap SUBMIT once all slots are filled to check your sequence!"
        ]
        overlay = InstructionOverlay(
            game_name=game_name,
            rules_list=rules,
            close_callback=self.on_instructions_closed
        )
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    # --- LIFECYCLE HANDLERS ---
    def on_pre_enter(self, *args):
        self.stop_game_engine()
        self.title_label.text = "SEQUENCE SWITCH"
        self.title_label.color = (0, 0.75, 1, 1)
        self.status_label.text = "FILL IN THE PATTERN"
        self.status_label.color = (1, 0.84, 0, 1)
        self.score = 0
        self.round_number = 1
        self.score_label.text = f"SCORE: {self.score}"
        self.load_high_score()
        self.hi_score_label.text = f"BEST: {self.high_score}"
        self.action_btn.text = "START GAME"
        self.action_btn.background_color = (0, 0.75, 1, 1)

    def on_leave(self, *args):
        self.stop_game_engine()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def go_back_to_menu(self, instance):
        self.stop_game_engine()
        self.manager.current = 'menu'

    # --- PERSISTENCE ---
    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
                    self.high_score = data.get('sequence_switch_high', 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['sequence_switch_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    # --- PATTERN GENERATOR ---
    def generate_pattern(self):
        """Generates a mathematical sequence and hides 2-3 values."""
        seq_len = 6
        pattern_type = random.choice(['ADD', 'SUB', 'MULT', 'STEP'])

        if self.round_number <= 3:
            pattern_type = random.choice(['ADD', 'SUB'])

        if pattern_type == 'ADD':
            step = random.randint(2, 9)
            start = random.randint(1, 20)
            seq = [start + (i * step) for i in range(seq_len)]
        elif pattern_type == 'SUB':
            step = random.randint(2, 8)
            start = random.randint(50, 99)
            seq = [start - (i * step) for i in range(seq_len)]
        elif pattern_type == 'MULT':
            step = random.choice([2, 3])
            start = random.randint(1, 5)
            seq = [start * (step ** i) for i in range(seq_len)]
        else:  # 'STEP' (+1, +2, +3, +4...)
            start = random.randint(1, 10)
            inc = random.randint(1, 3)
            seq = [start]
            curr = start
            for i in range(1, seq_len):
                curr += (inc + i - 1)
                seq.append(curr)

        self.full_sequence = seq

        # Pick 2-3 indices to hide
        num_missing = 3 if self.round_number >= 3 else 2
        missing_indices = sorted(random.sample(range(seq_len), num_missing))
        self.target_indices = missing_indices

        # Board state: None for missing slots, int for given numbers
        self.board_state = [
            None if idx in missing_indices else seq[idx]
            for idx in range(seq_len)
        ]

        # Generate Inventory Pool (Hidden correct answers + plausible distractors)
        hidden_answers = [seq[idx] for idx in missing_indices]
        distractors = set()

        while len(distractors) < (6 - len(hidden_answers)):
            d = random.choice(hidden_answers) + random.choice([-5, -3, -2, -1, 1, 2, 3, 5, 10])
            if d > 0 and d not in seq and d not in distractors:
                distractors.add(d)

        pool = hidden_answers + list(distractors)
        random.shuffle(pool)
        self.inventory_pool = pool

    # --- UI BOARD & BANK REFRESH ---
    def render_game_board(self):
        self.board_container.clear_widgets()
        self.board_buttons = []

        for idx, val in enumerate(self.board_state):
            is_hidden_slot = (idx in self.target_indices)
            is_selected = (idx == self.selected_slot_idx)

            if not is_hidden_slot:
                # Permanent Given Number Card
                btn = Button(
                    text=str(val),
                    font_name='assets/fonts/ARCADE_N.TTF',
                    font_size='14sp',
                    background_normal='',
                    background_color=(0.12, 0.16, 0.32, 1),
                    color=(1, 1, 1, 1),
                    disabled=True
                )
            else:
                # Fillable Slot
                if val is None:
                    disp_text = "[ ? ]"
                    text_color = (0, 0.75, 1, 1) if not is_selected else (1, 0.84, 0, 1)
                    bg_color = (0.08, 0.2, 0.4, 1) if is_selected else (0.06, 0.1, 0.24, 1)
                else:
                    disp_text = str(val)
                    text_color = (0.47, 0.87, 0.47, 1)  # Pastel Green placed answer
                    bg_color = (0.1, 0.3, 0.2, 1)

                btn = Button(
                    text=disp_text,
                    font_name='assets/fonts/ARCADE_N.TTF',
                    font_size='14sp',
                    background_normal='',
                    background_color=bg_color,
                    color=text_color
                )
                btn.slot_idx = idx
                btn.bind(on_release=self.handle_board_slot_tap)

            self.board_container.add_widget(btn)
            self.board_buttons.append(btn)

    def render_inventory_bank(self):
        self.bank_container.clear_widgets()
        self.inventory_buttons = []

        for idx, num in enumerate(self.inventory_pool):
            is_used = (num is None)

            btn = Button(
                text=str(num) if not is_used else "",
                font_name='assets/fonts/ARCADE_N.TTF',
                font_size='14sp',
                background_normal='',
                background_color=(0, 0.6, 0.8, 1) if not is_used else (0.05, 0.08, 0.18, 0.4),
                color=(1, 1, 1, 1) if not is_used else (0, 0, 0, 0),
                disabled=is_used
            )
            btn.tile_idx = idx
            btn.tile_val = num
            btn.bind(on_release=self.handle_bank_tile_tap)

            self.bank_container.add_widget(btn)
            self.inventory_buttons.append(btn)

    # --- INTERACTION LOGIC ---
    def handle_board_slot_tap(self, instance):
        if not self.game_active:
            return

        slot_idx = instance.slot_idx
        current_val = self.board_state[slot_idx]

        if current_val is not None:
            # Return placed tile back to bank
            for i in range(len(self.inventory_pool)):
                if self.inventory_pool[i] is None:
                    self.inventory_pool[i] = current_val
                    break

            self.board_state[slot_idx] = None
            self.selected_slot_idx = slot_idx
            trigger_haptic_feedback(0.04)
        else:
            # Highlight this empty slot
            if self.selected_slot_idx == slot_idx:
                self.selected_slot_idx = None  # Toggle deselect
            else:
                self.selected_slot_idx = slot_idx
            trigger_haptic_feedback(0.02)

        self.render_game_board()
        self.render_inventory_bank()

    def handle_bank_tile_tap(self, instance):
        if not self.game_active or instance.tile_val is None:
            return

        val = instance.tile_val
        tile_idx = instance.tile_idx

        # Target slot selection logic
        target_slot = self.selected_slot_idx

        # If no slot is explicitly highlighted, target first open empty slot
        if target_slot is None or self.board_state[target_slot] is not None:
            for idx in self.target_indices:
                if self.board_state[idx] is None:
                    target_slot = idx
                    break

        if target_slot is not None and self.board_state[target_slot] is None:
            trigger_haptic_feedback(0.04)
            self.board_state[target_slot] = val
            self.inventory_pool[tile_idx] = None
            self.selected_slot_idx = None

            self.render_game_board()
            self.render_inventory_bank()

    # --- GAME FLOW & ENGINE ---
    def handle_action_press(self, instance):
        if not self.game_active:
            self.start_game()
        else:
            self.verify_submission()

    def start_game(self):
        self.score = 0
        self.round_number = 1
        self.score_label.text = f"SCORE: {self.score}"
        self.action_btn.text = "SUBMIT"
        self.action_btn.background_color = (0, 0.75, 1, 1)
        self.start_round()

    def start_round(self):
        self.game_active = True
        self.selected_slot_idx = None
        self.status_label.text = f"ROUND {self.round_number}: COMPLETE THE PATTERN"
        self.status_label.color = (1, 0.84, 0, 1)
        self.action_btn.text = "SUBMIT"
        self.action_btn.background_color = (0, 0.75, 1, 1)

        self.generate_pattern()
        self.render_game_board()
        self.render_inventory_bank()

    def verify_submission(self):
        if not self.game_active:
            return

        # Check if all slots are filled
        if None in self.board_state:
            trigger_haptic_feedback(0.08)
            self.status_label.text = "FILL ALL SLOTS FIRST!"
            self.status_label.color = (0.9, 0.2, 0.2, 1)
            return

        # Verify pattern equality
        if self.board_state == self.full_sequence:
            trigger_haptic_feedback(0.12)
            self.score += 10
            self.round_number += 1
            self.score_label.text = f"SCORE: {self.score}"

            if self.score > self.high_score:
                self.high_score = self.score
                self.hi_score_label.text = f"BEST: {self.high_score}"
                self.save_high_score()

            self.status_label.text = "PERFECT PATTERN!"
            self.status_label.color = (0.47, 0.87, 0.47, 1)
            Clock.schedule_once(lambda dt: self.start_round(), 1.0)
        else:
            trigger_haptic_feedback(0.08)
            self.status_label.text = "INCORRECT! TRY AGAIN"
            self.status_label.color = (0.9, 0.2, 0.2, 1)

    def stop_game_engine(self):
        self.game_active = False
        self.selected_slot_idx = None
        self.board_container.clear_widgets()
        self.bank_container.clear_widgets()
        self.action_btn.text = "START GAME"
        self.action_btn.background_color = (0, 0.75, 1, 1)
        
# Directions: 0 = NORTH, 1 = EAST, 2 = SOUTH, 3 = WEST
OPPOSITE_DIR = {0: 2, 1: 3, 2: 0, 3: 1}
DIR_OFFSET = {
    0: (0, -1),  # North (Row - 1)
    1: (1, 0),   # East (Col + 1)
    2: (0, 1),   # South (Row + 1)
    3: (-1, 0)   # West (Col - 1)
}

COLOR_PALETTE = [
    {'name': 'Cyan', 'color': (0.0, 0.85, 1.0, 1.0), 'symbol': '▲'},
    {'name': 'Yellow', 'color': (1.0, 0.85, 0.0, 1.0), 'symbol': '■'},
    {'name': 'Pink', 'color': (1.0, 0.35, 0.7, 1.0), 'symbol': '●'},
    {'name': 'Green', 'color': (0.4, 0.9, 0.4, 1.0), 'symbol': '★'}
]


class TurnpikeTile(Button):
    def __init__(self, tile_type='elbow', initial_rotation=0, **kwargs):
        super().__init__(**kwargs)
        self.tile_type = tile_type
        self.rotation = initial_rotation
        self.background_normal = ''
        self.background_color = (0.08, 0.12, 0.24, 1)
        self.hole_info = None

        self.bind(pos=self.draw_tile, size=self.draw_tile)

    def rotate_tile(self):
        self.rotation = (self.rotation + 1) % 4
        self.draw_tile()

    def get_connections(self):
        base_connections = {
            'straight': {0, 2},
            'elbow': {0, 1},
            't_junction': {0, 1, 3},
            'cross': {0, 1, 2, 3}
        }
        raw = base_connections[self.tile_type]
        return {(d + self.rotation) % 4 for d in raw}

    def draw_tile(self, *args):
        self.canvas.after.clear()
        if self.width <= 1 or self.height <= 1:
            return

        with self.canvas.after:
            Color(0.2, 0.35, 0.65, 0.8)
            Line(rectangle=(self.x, self.y, self.width, self.height), width=dp(1))

            if self.hole_info:
                Color(*self.hole_info['color'])
                Ellipse(pos=(self.x + dp(4), self.y + dp(4)), size=(self.width - dp(8), self.height - dp(8)))
                Color(0.04, 0.06, 0.17, 1)
                Ellipse(pos=(self.x + dp(8), self.y + dp(8)), size=(self.width - dp(16), self.height - dp(16)))
                return

            Color(0, 0.85, 1, 1)
            cx, cy = self.center_x, self.center_y
            half_w, half_h = self.width / 2.0, self.height / 2.0
            w_line = dp(3)

            conns = self.get_connections()

            if len(conns) > 0:
                Ellipse(pos=(cx - dp(3), cy - dp(3)), size=(dp(6), dp(6)))

            if 0 in conns:
                Line(points=[cx, cy, cx, cy + half_h], width=w_line)
            if 1 in conns:
                Line(points=[cx, cy, cx + half_w, cy], width=w_line)
            if 2 in conns:
                Line(points=[cx, cy, cx, cy - half_h], width=w_line)
            if 3 in conns:
                Line(points=[cx, cy, cx - half_w, cy], width=w_line)


class TileTurnpikeScreen(Screen):
    GRID_SIZE = 7

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_active = False
        self.in_setup_phase = True
        self.setup_time_left = 30.0
        self.action_time_left = 90.0
        self.score = 0
        self.high_score = 0

        self.grid = []
        self.start_pos = (0, 3)
        self.active_balls = []
        self.target_holes = {}

        self.next_ball_color_idx = 0
        self.spawn_timer = 0.0
        self.spawn_interval = 2.5
        self.game_event = None

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        # Background
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.load_high_score()

        # HUD
        self.title_label = Label(
            text="TILE TURNPIKE",
            font_size='16sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.95}
        )
        self.layout.add_widget(self.title_label)

        self.score_label = Label(
            text="SCORE: 0",
            font_size='10sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1),
            pos_hint={'center_x': 0.25, 'center_y': 0.90}
        )
        self.layout.add_widget(self.score_label)

        self.timer_label = Label(
            text="SETUP: 30s",
            font_size='10sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 0.84, 0, 1),
            pos_hint={'center_x': 0.75, 'center_y': 0.90}
        )
        self.layout.add_widget(self.timer_label)

        self.status_label = Label(
            text="PRESS START TO REVEAL BOARD",
            font_size='8sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 0.84, 0, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.85}
        )
        self.layout.add_widget(self.status_label)

        # Back Button
        self.back_btn = Button(
            text="< MENU",
            font_size=Scale.font(15),
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05),
            pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='',
            background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        # Container
        self.play_area = RelativeLayout(
            size_hint=(0.92, 0.55),
            pos_hint={'center_x': 0.5, 'center_y': 0.52}
        )
        self.layout.add_widget(self.play_area)

        self.grid_layout = GridLayout(
            cols=self.GRID_SIZE,
            rows=self.GRID_SIZE,
            spacing=dp(2),
            size_hint=(1, 1),
            pos=(0, 0)
        )
        self.play_area.add_widget(self.grid_layout)

        self.overlay_widget = Widget(size_hint=(1, 1), pos=(0, 0))
        self.play_area.add_widget(self.overlay_widget)

        # Hide Board Initially
        self.play_area.opacity = 0

        # Action Buttons Row
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint=(0.9, 0.09),
            pos_hint={'center_x': 0.5, 'center_y': 0.12}
        )
        self.layout.add_widget(self.play_help_row)

        self.action_btn = Button(
            text="START GAME",
            font_size=Scale.font(25),
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1),
            size_hint_x=0.8,
            background_normal='',
            background_color=(0, 0.75, 1, 1)
        )
        self.action_btn.bind(on_release=self.handle_action_press)
        self.play_help_row.add_widget(self.action_btn)

        self.help_btn = Button(
            text="?",
            font_size='16sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='',
            background_color=(0, 0.5, 0.8, 1),
            color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        rules = [
            "Press START to reveal the board and launch the 30s setup phase",
            "SETUP PHASE (30s): Rotate tiles to make target color holes accessible",
            "ACTION PHASE: Balls spawn every 2.5s and take the shortest path to their target",
            "Rotate tiles dynamically during the action phase to redirect balls on the fly"
        ]
        overlay = InstructionOverlay("Tile Turnpike", rules, self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def on_pre_enter(self, *args):
        self.stop_game_engine()
        self.score = 0
        self.in_setup_phase = True
        self.setup_time_left = 30.0
        self.action_time_left = 90.0
        self.score_label.text = f"SCORE: {self.score}"
        self.timer_label.text = f"SETUP: {int(self.setup_time_left)}s"
        self.action_btn.text = "START GAME"
        self.action_btn.disabled = False
        self.status_label.text = "PRESS START TO REVEAL BOARD"
        self.status_label.color = (1, 0.84, 0, 1)
        
        self.play_area.opacity = 0  # Hide board until start

    def on_leave(self, *args):
        self.stop_game_engine()

    def go_back_to_menu(self, instance):
        self.stop_game_engine()
        self.manager.current = 'menu'

    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    self.high_score = json.load(f).get('tile_turnpike_high', 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['tile_turnpike_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    # --- GRID BUILDER ---
    def build_turnpike_grid(self):
        self.grid_layout.clear_widgets()
        self.grid = []
        tile_types = ['straight', 'elbow', 'elbow', 't_junction', 'cross']

        # 1. Build Grid Matrix
        for row in range(self.GRID_SIZE):
            row_tiles = []
            for col in range(self.GRID_SIZE):
                t_type = random.choice(tile_types)
                tile = TurnpikeTile(tile_type=t_type, initial_rotation=random.randint(0, 3))
                tile.bind(on_release=self.handle_tile_tap)
                row_tiles.append(tile)
            self.grid.append(row_tiles)

        # 2. Force Starting Tile (0, 3) to strictly be a 4-Way Cross Tile
        self.start_pos = (0, 3)
        start_r, start_c = self.start_pos
        start_tile = TurnpikeTile(tile_type='cross', initial_rotation=0)
        start_tile.bind(on_release=self.handle_tile_tap)
        self.grid[start_r][start_c] = start_tile

        # 3. Add All Tiles to the Kivy Grid Layout
        for row in self.grid:
            for tile in row:
                self.grid_layout.add_widget(tile)

        # 4. Place Border Holes
        border_positions = []
        for c in range(self.GRID_SIZE):
            if c != 3:
                border_positions.append((0, c))
            border_positions.append((self.GRID_SIZE - 1, c))
        for r in range(1, self.GRID_SIZE - 1):
            border_positions.append((r, 0))
            border_positions.append((r, self.GRID_SIZE - 1))

        chosen_holes = random.sample(border_positions, 4)
        self.target_holes = {}
        for idx, pos in enumerate(chosen_holes):
            r, c = pos
            self.target_holes[idx] = pos
            self.grid[r][c].hole_info = COLOR_PALETTE[idx]

        Clock.schedule_once(lambda dt: self._redraw_all_tiles(), 0.05)

    def _redraw_all_tiles(self):
        for row in self.grid:
            for tile in row:
                tile.draw_tile()

    def handle_tile_tap(self, instance):
        if not self.game_active or instance.hole_info:
            return
        trigger_haptic_feedback(0.03)
        instance.rotate_tile()

    # --- GAME ENGINE ---
    def handle_action_press(self, instance):
        if not self.game_active:
            self.start_game()
        elif self.in_setup_phase:
            self.transition_to_action_phase()

    def start_game(self):
        self.build_turnpike_grid()
        self.play_area.opacity = 1  # Reveal board

        self.game_active = True
        self.in_setup_phase = True
        self.setup_time_left = 30.0
        self.action_time_left = 90.0
        self.active_balls = []
        self.spawn_timer = 0.0
        self.next_ball_color_idx = random.randint(0, 3)

        self.action_btn.text = "READY! (SKIP SETUP)"
        self.status_label.text = "SETUP PHASE: CONNECT ALL HOLES!"
        self.status_label.color = (0.47, 0.87, 0.47, 1)

        if self.game_event:
            Clock.unschedule(self.game_event)
        self.game_event = Clock.schedule_interval(self.game_loop_tick, 1.0 / 60.0)

    def transition_to_action_phase(self):
        self.in_setup_phase = False
        self.status_label.text = "ACTION PHASE: BALLS SPAWNING!"
        self.status_label.color = (1, 0.84, 0, 1)
        self.action_btn.disabled = True
        self.action_btn.text = "ROLLING..."
        self.spawn_timer = 2.0

    def game_loop_tick(self, dt):
        if not self.game_active:
            return

        if self.in_setup_phase:
            self.setup_time_left -= dt
            self.timer_label.text = f"SETUP: {max(0, int(self.setup_time_left))}s"
            if self.setup_time_left <= 0:
                self.transition_to_action_phase()
            self.draw_overlay_graphics()
            return

        self.action_time_left -= dt
        self.timer_label.text = f"TIME: {max(0, int(self.action_time_left))}s"
        if self.action_time_left <= 0:
            self.end_game()
            return

        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            self.spawn_ball()

        # Fluid movement scaling using frame delta dt
        ball_speed = 1.25  # Smooth tile transitions/sec
        for ball in self.active_balls[:]:
            ball['progress'] += ball_speed * dt
            if ball['progress'] >= 1.0:
                ball['progress'] -= 1.0
                self.advance_ball_with_ai(ball)

        self.draw_overlay_graphics()

    def spawn_ball(self):
        self.active_balls.append({
            'color_idx': self.next_ball_color_idx,
            'pos': list(self.start_pos),
            'entry_dir': 0,
            'progress': 0.0
        })
        self.next_ball_color_idx = random.randint(0, 3)

    # --- SHORTEST-PATH BFS AI ---
    def find_best_exit_direction(self, row, col, entry_dir, target_color_idx):
        current_tile = self.grid[row][col]
        conns = current_tile.get_connections()

        if entry_dir not in conns:
            return None  # Dead end

        available_exits = [d for d in conns if d != entry_dir]
        if not available_exits:
            return entry_dir

        if len(available_exits) == 1:
            return available_exits[0]

        target_pos = self.target_holes[target_color_idx]

        # Evaluate distance to target for each branch
        shortest_dist = float('inf')
        best_exit = available_exits[0]

        for exit_dir in available_exits:
            dist = self.get_bfs_distance_to_target((row, col), exit_dir, target_pos)
            if dist < shortest_dist:
                shortest_dist = dist
                best_exit = exit_dir

        return best_exit

    def get_bfs_distance_to_target(self, start_grid, start_exit_dir, target_grid):
        """Returns the exact shortest step count to target_grid, or infinity if no route exists."""
        queue = deque()
        dc, dr = DIR_OFFSET[start_exit_dir]
        next_r, next_c = start_grid[0] + dr, start_grid[1] + dc

        queue.append((next_r, next_c, OPPOSITE_DIR[start_exit_dir], 1))
        visited = set()

        while queue:
            r, c, entry_d, dist = queue.popleft()

            if (r, c) == target_grid:
                return dist

            if not (0 <= r < self.GRID_SIZE and 0 <= c < self.GRID_SIZE) or (r, c, entry_d) in visited:
                continue

            visited.add((r, c, entry_d))
            tile = self.grid[r][c]
            if tile.hole_info:
                continue

            conns = tile.get_connections()
            if entry_d in conns:
                for exit_d in conns:
                    if exit_d != entry_d:
                        off_c, off_r = DIR_OFFSET[exit_d]
                        queue.append((r + off_r, c + off_c, OPPOSITE_DIR[exit_d], dist + 1))

        return float('inf')

    def advance_ball_with_ai(self, ball):
        r, c = ball['pos']
        exit_dir = self.find_best_exit_direction(r, c, ball['entry_dir'], ball['color_idx'])

        if exit_dir is None:
            self.remove_ball_and_score(ball, success=False, msg="DEAD END!")
            return

        dc, dr = DIR_OFFSET[exit_dir]
        next_r, next_c = r + dr, c + dc

        if not (0 <= next_r < self.GRID_SIZE and 0 <= next_c < self.GRID_SIZE):
            self.remove_ball_and_score(ball, success=False, msg="OFF GRID!")
            return

        next_tile = self.grid[next_r][next_c]
        if next_tile.hole_info:
            target_pos = self.target_holes[ball['color_idx']]
            if (next_r, next_c) == target_pos:
                self.remove_ball_and_score(ball, success=True, msg="GOAL MATCH!")
            else:
                self.remove_ball_and_score(ball, success=False, msg="WRONG HOLE!")
            return

        ball['pos'] = [next_r, next_c]
        ball['entry_dir'] = OPPOSITE_DIR[exit_dir]

    def remove_ball_and_score(self, ball, success, msg):
        if ball in self.active_balls:
            self.active_balls.remove(ball)

        if success:
            trigger_haptic_feedback(0.1)
            self.score += 15
            self.status_label.text = f"{msg} +15 PTS"
            self.status_label.color = (0.47, 0.87, 0.47, 1)
        else:
            trigger_haptic_feedback(0.15)
            self.score = max(0, self.score - 10)
            self.status_label.text = f"{msg} -10 PTS"
            self.status_label.color = (0.9, 0.2, 0.2, 1)

        self.score_label.text = f"SCORE: {self.score}"

    # --- SMOOTH RENDER OVERLAY ---
    def draw_overlay_graphics(self):
        self.overlay_widget.canvas.clear()
        if not self.game_active or self.play_area.opacity == 0:
            return

        # Start Ring Indicator
        start_tile = self.grid[self.start_pos[0]][self.start_pos[1]]
        cx, cy = start_tile.center_x, start_tile.center_y
        next_color_data = COLOR_PALETTE[self.next_ball_color_idx]

        with self.overlay_widget.canvas:
            Color(*next_color_data['color'])
            Line(circle=(cx, cy, dp(16)), width=dp(2.5))

        # Smooth Ball Interpolation
        if not self.in_setup_phase:
            with self.overlay_widget.canvas:
                for ball in self.active_balls:
                    r, c = ball['pos']
                    tile = self.grid[r][c]
                    cx, cy = tile.center_x, tile.center_y
                    half_w, half_h = tile.width / 2.0, tile.height / 2.0

                    if ball['entry_dir'] == 0:
                        start_x, start_y = cx, cy + half_h
                    elif ball['entry_dir'] == 1:
                        start_x, start_y = cx + half_w, cy
                    elif ball['entry_dir'] == 2:
                        start_x, start_y = cx, cy - half_h
                    else:
                        start_x, start_y = cx - half_w, cy

                    # Parametric position calculation
                    p = min(1.0, ball['progress'])
                    curr_x = start_x + (cx - start_x) * min(1.0, p * 2.0)
                    curr_y = start_y + (cy - start_y) * min(1.0, p * 2.0)

                    c_info = COLOR_PALETTE[ball['color_idx']]
                    Color(*c_info['color'])
                    radius = dp(7.5)
                    Ellipse(pos=(curr_x - radius, curr_y - radius), size=(radius * 2, radius * 2))

    def end_game(self):
        self.stop_game_engine()
        self.status_label.text = f"TIME'S UP! FINAL SCORE: {self.score}"
        self.status_label.color = (1, 0.84, 0, 1)
        self.action_btn.disabled = False
        self.action_btn.text = "PLAY AGAIN"

        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()

    def stop_game_engine(self):
        self.game_active = False
        if self.game_event:
            Clock.unschedule(self.game_event)
            self.game_event = None
        self.overlay_widget.canvas.clear()
        
# Direction Vectors: (dx, dy) in grid space
DIR_UP = (0, 1)
DIR_DOWN = (0, -1)
DIR_LEFT = (-1, 0)
DIR_RIGHT = (1, 0)

# Neon Color Palette Cycle
NEON_COLORS = [
    {'name': 'Pink', 'rgb': (1.0, 0.2, 0.8, 1.0)},
    {'name': 'Green', 'rgb': (0.2, 1.0, 0.3, 1.0)},
    {'name': 'Cyan', 'rgb': (0.0, 0.9, 1.0, 1.0)},
    {'name': 'Yellow', 'rgb': (1.0, 0.9, 0.1, 1.0)}
]


class NeonPythonScreen(Screen):
    # Reasonable Portrait Mobile Grid Arena Size
    GRID_COLS = 20
    GRID_ROWS = 20

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_active = False
        self.score = 0
        self.high_score = 0

        # Snake state
        self.snake_body = []  # List of (col, row) tuples
        self.direction = DIR_RIGHT
        self.next_direction = DIR_RIGHT
        self.color_index = 0

        # Food target
        self.food_pos = (0, 0)  # (col, row)

        # Touch tracking for swipes
        self.touch_start_pos = None

        self.game_event = None
        self.move_interval = 0.12  # Speed tick in seconds

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        # Dark Background
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.load_high_score()

        # Header HUD
        self.title_label = Label(
            text="NEON PYTHON",
            font_size='16sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.9, 1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.95}
        )
        self.layout.add_widget(self.title_label)

        self.score_label = Label(
            text="SCORE: 0",
            font_size='10sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.2, 1.0, 0.3, 1),
            pos_hint={'center_x': 0.25, 'center_y': 0.90}
        )
        self.layout.add_widget(self.score_label)

        self.high_label = Label(
            text=f"HIGH: {self.high_score}",
            font_size='10sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 0.9, 0.1, 1),
            pos_hint={'center_x': 0.75, 'center_y': 0.90}
        )
        self.layout.add_widget(self.high_label)

        self.status_label = Label(
            text="SWIPE OR USE WASD TO START",
            font_size='8sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 1, 1, 0.8),
            pos_hint={'center_x': 0.5, 'center_y': 0.85}
        )
        self.layout.add_widget(self.status_label)

        # Back Button
        self.back_btn = Button(
            text="< MENU",
            font_size=Scale.font(15),
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05),
            pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='',
            background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        # Arena Play Area Container
        self.arena_area = Widget(
            size_hint=(0.90, 0.65),
            pos_hint={'center_x': 0.5, 'center_y': 0.48}
        )
        self.layout.add_widget(self.arena_area)

        # Controls Row
        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint=(0.9, 0.08),
            pos_hint={'center_x': 0.5, 'center_y': 0.08}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME",
            font_size=Scale.font(25),
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1),
            size_hint_x=0.8,
            background_normal='',
            background_color=(0, 0.9, 1, 1)
        )
        self.start_btn.bind(on_release=self.start_game)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?",
            font_size='16sp',
            font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='',
            background_color=(0, 0.5, 0.8, 1),
            color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        rules = [
            "Swipe on mobile or use WASD / Arrow keys on PC to steer",
            "Eat white neon target circles to grow your snake",
            "Each food eaten cycles your snake's color through neon pink, green, cyan, and yellow",
            "Avoid running into walls or biting your own tail!"
        ]
        overlay = InstructionOverlay("Neon Python", rules, self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def on_pre_enter(self, *args):
        # Bind keyboard listener for WASD testing
        Window.bind(on_key_down=self._on_keyboard_down)
        self.stop_game()
        self.status_label.text = "PRESS START TO BEGIN"

    def on_leave(self, *args):
        Window.unbind(on_key_down=self._on_keyboard_down)
        self.stop_game()

    def go_back_to_menu(self, instance):
        self.stop_game()
        self.manager.current = 'menu'

    # --- INPUT HANDLERS (WASD & SWIPES) ---
    def _on_keyboard_down(self, window, key, scancode, codepoint, modifier):
        if not self.game_active:
            return

        # W/Up, S/Down, A/Left, D/Right
        if codepoint == 'w' or key == 273:
            if self.direction != DIR_DOWN:
                self.next_direction = DIR_UP
        elif codepoint == 's' or key == 274:
            if self.direction != DIR_UP:
                self.next_direction = DIR_DOWN
        elif codepoint == 'a' or key == 276:
            if self.direction != DIR_RIGHT:
                self.next_direction = DIR_LEFT
        elif codepoint == 'd' or key == 275:
            if self.direction != DIR_LEFT:
                self.next_direction = DIR_RIGHT

    def on_touch_down(self, touch):
        if self.game_active and self.arena_area.collide_point(*touch.pos):
            self.touch_start_pos = touch.pos
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.game_active and self.touch_start_pos:
            dx = touch.x - self.touch_start_pos[0]
            dy = touch.y - self.touch_start_pos[1]
            self.touch_start_pos = None

            min_swipe = dp(20)
            if abs(dx) > min_swipe or abs(dy) > min_swipe:
                trigger_haptic_feedback(0.02)
                if abs(dx) > abs(dy):
                    # Horizontal swipe
                    if dx > 0 and self.direction != DIR_LEFT:
                        self.next_direction = DIR_RIGHT
                    elif dx < 0 and self.direction != DIR_RIGHT:
                        self.next_direction = DIR_LEFT
                else:
                    # Vertical swipe
                    if dy > 0 and self.direction != DIR_DOWN:
                        self.next_direction = DIR_UP
                    elif dy < 0 and self.direction != DIR_UP:
                        self.next_direction = DIR_DOWN
                return True
        return super().on_touch_up(touch)

    # --- GAME LOOP & LOGIC ---
    def start_game(self, *args):
        self.game_active = True
        self.score = 0
        self.color_index = 0
        self.direction = DIR_RIGHT
        self.next_direction = DIR_RIGHT

        # Center snake initialization
        mid_c, mid_r = self.GRID_COLS // 2, self.GRID_ROWS // 2
        self.snake_body = [(mid_c, mid_r), (mid_c - 1, mid_r), (mid_c - 2, mid_r)]

        self.spawn_food()

        self.score_label.text = f"SCORE: {self.score}"
        self.status_label.text = "SWIPE / WASD TO STEER"
        self.start_btn.text = "RESTART"

        if self.game_event:
            Clock.unschedule(self.game_event)
        self.game_event = Clock.schedule_interval(self.game_tick, self.move_interval)

    def spawn_food(self):
        empty_cells = [
            (c, r) for c in range(self.GRID_COLS) for r in range(self.GRID_ROWS)
            if (c, r) not in self.snake_body
        ]
        if empty_cells:
            self.food_pos = random.choice(empty_cells)

    def game_tick(self, dt):
        if not self.game_active:
            return

        self.direction = self.next_direction
        head_c, head_r = self.snake_body[0]
        dx, dy = self.direction
        new_head = (head_c + dx, head_r + dy)

        # Check Wall Collision
        if not (0 <= new_head[0] < self.GRID_COLS and 0 <= new_head[1] < self.GRID_ROWS):
            self.end_game("CRASHED INTO WALL!")
            return

        # Check Self Collision
        if new_head in self.snake_body:
            self.end_game("BIT YOURSELF!")
            return

        self.snake_body.insert(0, new_head)

        # Check Food Collision
        if new_head == self.food_pos:
            trigger_haptic_feedback(0.08)
            self.score += 10
            self.color_index = (self.color_index + 1) % len(NEON_COLORS)  # Cycle color
            self.score_label.text = f"SCORE: {self.score}"
            self.spawn_food()
        else:
            self.snake_body.pop()

        self.render_arena()

    # --- RENDERING ---
    def render_arena(self):
        self.arena_area.canvas.before.clear()
        self.arena_area.canvas.clear()

        w, h = self.arena_area.size
        ax, ay = self.arena_area.pos
        cell_w = w / float(self.GRID_COLS)
        cell_h = h / float(self.GRID_ROWS)

        with self.arena_area.canvas.before:
            # Outer Grid Border
            Color(0.15, 0.25, 0.5, 0.8)
            Line(rectangle=(ax, ay, w, h), width=dp(2))

        with self.arena_area.canvas:
            # 1. Render White Food Target
            fx = ax + self.food_pos[0] * cell_w + cell_w * 0.15
            fy = ay + self.food_pos[1] * cell_h + cell_h * 0.15
            fw = cell_w * 0.7
            fh = cell_h * 0.7
            Color(1.0, 1.0, 1.0, 1.0)
            Ellipse(pos=(fx, fy), size=(fw, fh))

            # 2. Render Neon Snake
            current_neon = NEON_COLORS[self.color_index]['rgb']
            Color(*current_neon)

            for i, (c, r) in enumerate(self.snake_body):
                sx = ax + c * cell_w + cell_w * 0.08
                sy = ay + r * cell_h + cell_h * 0.08
                sw = cell_w * 0.84
                sh = cell_h * 0.84

                # Draw Head slightly rounded / distinct
                if i == 0:
                    Ellipse(pos=(sx, sy), size=(sw, sh))
                else:
                    Rectangle(pos=(sx, sy), size=(sw, sh))

    def end_game(self, reason):
        trigger_haptic_feedback(0.2)
        self.stop_game()
        self.status_label.text = f"{reason} FINAL SCORE: {self.score}"
        self.start_btn.text = "PLAY AGAIN"

        if self.score > self.high_score:
            self.high_score = self.score
            self.high_label.text = f"HIGH: {self.high_score}"
            self.save_high_score()

    def stop_game(self):
        self.game_active = False
        if self.game_event:
            Clock.unschedule(self.game_event)
            self.game_event = None

    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    self.high_score = json.load(f).get('neon_python_high', 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r') as f:
                    data = json.load(f)
            data['neon_python_high'] = self.high_score
            with open('save_data.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass
        
class LockPickScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_active = False
        self.is_frozen = False
        self.freeze_timer = 0.0
        self.score = 0
        self.high_score = 0
        self.time_remaining = 60.0
        self.level = 1

        # Circle & Orbit Mechanics (Tracked in Radians)
        self.angle_rad = 0.0
        self.orbit_speed_rad = math.radians(130.0)  # Radians per second
        self.orbit_direction = 1
        self.targets = []
        self.target_drift_speed_rad = 0.0

        self.game_event = None

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        # 1. Deep Cosmic Background Layer (#0A0F2C)
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.load_high_score()

        # 2. Standardized Retro HUD Elements
        self.title_label = Label(
            text="LOCK PICK", font_size=Scale.font(30), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.92}
        )
        self.layout.add_widget(self.title_label)

        self.timer_label = Label(
            text="TIME: 60s", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.80}
        )
        self.layout.add_widget(self.timer_label)

        self.score_label = Label(
            text="SCORE: 0", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.3, 'center_y': 0.86}
        )
        self.layout.add_widget(self.score_label)

        self.hi_score_label = Label(
            text=f"BEST: {self.high_score}", font_size='12sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.7, 'center_y': 0.86}
        )
        self.layout.add_widget(self.hi_score_label)

        self.status_label = Label(
            text="", font_size='16sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.9, 0.2, 0.2, 1), pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.layout.add_widget(self.status_label)

        # Standard Top-Left Back Button
        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        # 3. Standardized Control Row (Play & Help)
        self.play_help_row = BoxLayout(
            orientation='horizontal', spacing=dp(10),
            size_hint=(0.9, 0.1), pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), size_hint_x=0.8,
            background_normal='', background_color=(0, 0.75, 1, 1)
        )
        self.start_btn.bind(on_release=self.start_game)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size='16sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

    # --- INSTRUCTIONS OVERLAY ---
    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        rules = [
            "A triangle orbits around the lock cylinder",
            "Tap anywhere when the triangle touches a DARK RED section",
            "Turn all sections green to break the lock combination",
            "Level 3+: Correct taps invert orbit direction!",
            "Missed taps jam your pick for a 1-second penalty freeze!"
        ]
        overlay = InstructionOverlay(
            game_name="Lock Pick",
            rules_list=rules,
            close_callback=self.on_instructions_closed
        )
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    # --- LIFECYCLE HANDLERS ---
    def on_pre_enter(self, *args):
        self.stop_game_engine()
        self.title_label.text = "LOCK PICK"
        self.title_label.color = (0, 0.75, 1, 1)
        self.timer_label.text = "TIME: 60s"
        self.score_label.text = "SCORE: 0"
        self.status_label.text = ""
        self.load_high_score()
        self.hi_score_label.text = f"BEST: {self.high_score}"
        if self.play_help_row not in self.layout.children:
            self.layout.add_widget(self.play_help_row)
        self.play_help_row.disabled = False

    def on_leave(self, *args):
        self.stop_game_engine()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.draw_lock_canvas()

    def go_back_to_menu(self, instance):
        self.stop_game_engine()
        self.manager.current = 'menu'

    # --- SAVE / LOAD DATA ---
    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.high_score = data.get('lock_pick_high', 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
            data['lock_pick_high'] = self.high_score
            with open('save_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception:
            pass

    # --- GAME GENERATION & ENGINE ---
    def generate_lock_combination(self):
        self.targets = []
        num_targets = min(2 + (self.level // 2), 6)
        base_sweep_deg = max(22.0 - (self.level * 0.8), 8.0)
        
        self.orbit_speed_rad = math.radians(130.0 + (self.level * 15.0))

        if self.level >= 5:
            self.target_drift_speed_rad = math.radians((random.choice([-1, 1])) * (10.0 + self.level * 2))
        else:
            self.target_drift_speed_rad = 0.0

        sector_deg = 360.0 / num_targets
        for i in range(num_targets):
            variation = random.uniform(0.85, 1.15)
            sweep_deg = max(base_sweep_deg * variation, 6.0)
            min_deg = i * sector_deg
            max_deg = (i + 1) * sector_deg - sweep_deg
            start_deg = random.uniform(min_deg, max_deg)

            self.targets.append({
                'start_rad': math.radians(start_deg % 360.0),
                'sweep_rad': math.radians(sweep_deg),
                'unlocked': False
            })

    def start_game(self, instance=None):
        if self.play_help_row in self.layout.children:
            self.layout.remove_widget(self.play_help_row)

        self.score = 0
        self.level = 1
        self.time_remaining = 60.0
        self.game_active = True
        self.is_frozen = False
        self.angle_rad = 0.0
        self.orbit_direction = 1
        
        self.score_label.text = "SCORE: 0"
        self.timer_label.text = "TIME: 60s"
        self.status_label.text = ""

        self.generate_lock_combination()

        if self.game_event:
            Clock.unschedule(self.game_event)
        self.game_event = Clock.schedule_interval(self.game_loop_tick, 1.0 / 60.0)

    def on_touch_down(self, touch):
        if self.back_btn.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        if not self.game_active or self.is_frozen:
            return super().on_touch_down(touch)

        self.evaluate_tap()
        return True

    def evaluate_tap(self):
        curr_rad = self.angle_rad % (2 * math.pi)
        hit = False
        
        # Fair hit tolerance padding (~5 degrees)
        tolerance_rad = math.radians(5.0)

        for target in self.targets:
            if target['unlocked']:
                continue

            start_rad = target['start_rad'] % (2 * math.pi)
            sweep_rad = target['sweep_rad']

            # Distance from start of arc going forward counter-clockwise
            forward_dist = (curr_rad - start_rad) % (2 * math.pi)
            # Distance from start of arc going backward
            backward_dist = (start_rad - curr_rad) % (2 * math.pi)

            # Hit registers if triangle tip is inside arc OR within tolerance of either edge
            if forward_dist <= (sweep_rad + tolerance_rad) or backward_dist <= tolerance_rad:
                hit = True
                target['unlocked'] = True
                break

        if hit:
            trigger_haptic_feedback(0.04)
            self.score += 1
            self.score_label.text = f"SCORE: {self.score}"
            
            # Reversal difficulty modifier kicks in at Level 3+
            if self.level >= 3:
                self.orbit_direction *= -1

            if all(t['unlocked'] for t in self.targets):
                self.level += 1
                self.generate_lock_combination()
        else:
            trigger_haptic_feedback(0.12)
            self.is_frozen = True
            self.freeze_timer = 1.0
            self.status_label.text = "JAMMED!"

    def game_loop_tick(self, dt):
        if not self.game_active:
            return

        self.time_remaining -= dt
        if self.time_remaining <= 0:
            self.time_remaining = 0
            self.stop_game_engine()
            return

        self.timer_label.text = f"TIME: {int(self.time_remaining)}s"

        if self.is_frozen:
            self.freeze_timer -= dt
            if self.freeze_timer <= 0:
                self.is_frozen = False
                self.status_label.text = ""
            self.draw_lock_canvas()
            return

        self.angle_rad = (self.angle_rad + (self.orbit_speed_rad * self.orbit_direction) * dt) % (2 * math.pi)

        if self.target_drift_speed_rad != 0:
            for t in self.targets:
                t['start_rad'] = (t['start_rad'] + self.target_drift_speed_rad * dt) % (2 * math.pi)

        self.draw_lock_canvas()

    def draw_lock_canvas(self):
        self.canvas.remove_group('lockpick_shapes')
        if not self.game_active:
            return

        cx = Window.width / 2.0
        cy = Window.height * 0.52
        r = min(Window.width, Window.height) * 0.28
        thickness = dp(10)

        with self.canvas:
            # 1. Base Lock Ring
            Color(1, 1, 1, 0.3 if self.is_frozen else 1.0, group='lockpick_shapes')
            Line(circle=(cx, cy, r), width=dp(3), group='lockpick_shapes')

            # 2. Target Segments (Drawn explicitly using trig points for 100% precision match)
            for target in self.targets:
                if target['unlocked']:
                    Color(0.1, 0.9, 0.3, 1, group='lockpick_shapes')  # Green
                else:
                    Color(0.8, 0.15, 0.15, 1, group='lockpick_shapes')  # Dark Red

                arc_points = []
                steps = 24
                for i in range(steps + 1):
                    a = target['start_rad'] + (target['sweep_rad'] * (i / float(steps)))
                    arc_points.extend([cx + r * math.cos(a), cy + r * math.sin(a)])

                Line(points=arc_points, width=thickness, cap='none', group='lockpick_shapes')

            # 3. Orbiting Pointer (Equilateral Triangle, tip touching outer ring edge)
            rad = self.angle_rad
            side = dp(12)
            height = (math.sqrt(3) / 2.0) * side

            tip_dist = r + (thickness / 2.0) + dp(1)
            base_dist = tip_dist + height
            spread_angle = (side / 2.0) / base_dist

            p1 = (cx + tip_dist * math.cos(rad), cy + tip_dist * math.sin(rad))
            p2 = (cx + base_dist * math.cos(rad - spread_angle), cy + base_dist * math.sin(rad - spread_angle))
            p3 = (cx + base_dist * math.cos(rad + spread_angle), cy + base_dist * math.sin(rad + spread_angle))

            Color(1, 1, 1, 1, group='lockpick_shapes')
            Mesh(
                vertices=[p1[0], p1[1], 0, 0, p2[0], p2[1], 0, 0, p3[0], p3[1], 0, 0],
                indices=[0, 1, 2],
                mode='triangles',
                group='lockpick_shapes'
            )

    def stop_game_engine(self):
        self.game_active = False
        if self.game_event:
            Clock.unschedule(self.game_event)
            self.game_event = None

        self.canvas.remove_group('lockpick_shapes')
        self.status_label.text = "TIME UP!"

        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
            self.title_label.text = "NEW HIGH SCORE!"
            self.title_label.color = (1, 0.84, 0, 1)

        self.hi_score_label.text = f"BEST: {self.high_score}"
        self.start_btn.text = "PLAY AGAIN"

        if self.play_help_row not in self.layout.children:
            self.play_help_row.disabled = False
            self.layout.add_widget(self.play_help_row)
            
class RapidReaderScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_active = False
        self.round_number = 1
        self.score = 0
        self.high_score = 0
        
        # Word Banks (Expanded)
        self.word_banks = {
            'ADJECTIVE_1': ['energetic', 'quiet', 'nervous', 'glowing', 'radioactive', 'invisible', 'furious', 'sleepy', 'gigantic', 'hungry'],
            'SUBJECT_1': ['boy', 'athlete', 'teacher', 'cowboy', 'astronaut', 'penguin', 'detective', 'chef', 'pirate', 'robot'],
            'VERB_1_PAST': ['kicked', 'dropped', 'found', 'petted', 'hypnotized', 'toasted', 'launched', 'spotted', 'painted', 'juggled'],
            'OBJECT_1': ['soccer ball', 'leather shoe', 'wallet', 'Ferrari', 'bowling pin', 'saxophone', 'watermelon', 'laptop', 'treasure map', 'goldfish'],
            'LOCATION_1': ['park', 'stadium', 'hallway', 'hair salon', 'submarine', 'graveyard', 'bakery', 'library', 'airport', 'castle'],
            'ADJECTIVE_2': ['strict', 'clumsy', 'tall', 'tiny', 'robotic', 'dramatic', 'grumpy', 'wild', 'mysterious', 'fancy'],
            'SUBJECT_2': ['referee', 'landlord', 'police officer', 'wizard', 'mime', 'raccoon', 'ninja', 'alien', 'captain', 'barber'],
            'ADVERB_1': ['aggressively', 'accidentally', 'quietly', 'triumphantly', 'suspiciously', 'wildly', 'politely', 'eagerly', 'boldly', 'calmly'],
            'VERB_2_PAST': ['poked', 'nudged', 'tapped', 'slapped', 'serenaded', 'tickled', 'blasted', 'chased', 'greeted', 'scared'],
            'OBJECT_2': ['whistle', 'clipboard', 'flashlight', 'baguette', 'rubber chicken', 'spatula', 'umbrella', 'laser pointer', 'broom', 'feather'],
            'VERB_3_BASE': ['launch', 'roll', 'slide', 'fling', 'teleport', 'yeet', 'bounce', 'throw', 'drag', 'spin'],
            'LOCATION_2': ['dugout', 'concession stand', 'office', 'dumpster', 'spaceship', 'VIP lounge', 'greenhouse', 'treehouse', 'vault', 'bunker'],
            'ADJECTIVE_3': ['shiny', 'forgotten', 'heavy', 'cursed', 'giant', 'marshmallow', 'ancient', 'golden', 'frozen', 'magical'],
            'OBJECT_3': ['trophy', 'key', 'gold coin', 'disco ball', 'slice of pizza', 'lawnmower', 'crown', 'crystal ball', 'magic wand', 'diamond'],
            'VERB_4_PAST': ['cheered', 'sighed', 'bowed', 'danced', 'gasped', 'backflipped', 'screamed', 'laughed', 'clapped', 'fainted'],
            'ADVERB_2': ['loudly', 'relievedly', 'politely', 'hysterically', 'awkwardly', 'violently', 'joyfully', 'dramatically', 'peacefully', 'proudly'],
            'VERB_5_BASE': ['celebrate', 'rest', 'wait', 'hibernate', 'meditate', 'juggle', 'party', 'sleep', 'hide', 'feast'],
            'TIME_FRAME': ['midnight', 'sunset', 'tomorrow', 'Tuesday', 'the apocalypse', 'next century', 'breakfast', 'next year', 'dawn', 'noon']
        }

        # Game State Handles
        self.current_story_words = []
        self.current_word_idx = 0
        self.story_variables = {}
        self.questions_queue = []
        self.current_question = None
        self.timer_event = None
        self.countdown_ticks = 3
        
        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        # 1. Background Layer (#0A0F2C)
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.load_high_score()

        # 2. Retro HUD
        self.title_label = Label(
            text="RAPID READER", font_size=Scale.font(30), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.92}
        )
        self.layout.add_widget(self.title_label)

        self.score_label = Label(
            text="SCORE: 0", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.3, 'center_y': 0.85}
        )
        self.layout.add_widget(self.score_label)

        self.hi_score_label = Label(
            text=f"BEST: {self.high_score}", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), pos_hint={'center_x': 0.7, 'center_y': 0.85}
        )
        self.layout.add_widget(self.hi_score_label)

        self.wpm_label = Label(
            text="SPEED: 200 WPM", font_size='10sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 0.84, 0, 1), pos_hint={'center_x': 0.5, 'center_y': 0.78}
        )
        self.layout.add_widget(self.wpm_label)

        # 3. RSVP Reading Display Box (High Contrast Yellow Box + Black Bold Text)
        self.rsvp_container = RelativeLayout(
            size_hint=(0.85, 0.18), pos_hint={'center_x': 0.5, 'center_y': 0.55}
        )
        with self.rsvp_container.canvas.before:
            Color(1, 0.85, 0, 1)  # Vivid Arcade Yellow
            self.rsvp_bg = Rectangle(pos=(0, 0), size=self.rsvp_container.size)
            Color(0, 0, 0, 1)     # Solid Black Border
            self.rsvp_border = Line(rectangle=(0, 0, Window.width * 0.85, Window.height * 0.18), width=dp(3))
            
        self.rsvp_container.bind(size=self.sync_rsvp_box, pos=self.sync_rsvp_box)
        self.layout.add_widget(self.rsvp_container)

        self.rsvp_label = Label(
            text="READY?", font_size=Scale.font(20), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0, 0, 1), pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='center', valign='middle'
        )
        self.rsvp_container.add_widget(self.rsvp_label)

        # 4. Multiple Choice Questions Container (Initially Hidden)
        self.mcq_container = RelativeLayout(
            size_hint=(0.9, 0.45), pos_hint={'center_x': 0.5, 'center_y': 0.42},
            opacity=0, disabled=True
        )
        self.layout.add_widget(self.mcq_container)

        self.q_prompt_label = Label(
            text="Question?", font_size='11sp', font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 1, 1, 1), pos_hint={'center_x': 0.5, 'top': 1.0},
            size_hint=(1, 0.22), halign='center', valign='middle'
        )
        self.q_prompt_label.bind(size=self.q_prompt_label.setter('text_size'))
        self.mcq_container.add_widget(self.q_prompt_label)

        self.options_grid = GridLayout(
            cols=1, rows=4, spacing=dp(8), size_hint=(1, 0.75), pos_hint={'center_x': 0.5, 'y': 0.0}
        )
        self.option_buttons = []
        for i in range(4):
            btn = Button(
                text="", font_size='10sp', font_name='assets/fonts/ARCADE_N.TTF',
                color=(0.04, 0.06, 0.17, 1), background_normal='', background_color=(0, 0.75, 1, 1)
            )
            btn.option_idx = i
            btn.bind(on_release=self.handle_answer_selection)
            self.options_grid.add_widget(btn)
            self.option_buttons.append(btn)
        self.mcq_container.add_widget(self.options_grid)

        # 5. Back Button
        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        # 6. Action Control Row
        self.play_help_row = BoxLayout(
            orientation='horizontal', spacing=dp(10),
            size_hint=(0.9, 0.1), pos_hint={'center_x': 0.5, 'center_y': 0.12}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(20), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), size_hint_x=0.8,
            background_normal='', background_color=(0, 0.75, 1, 1)
        )
        self.start_btn.bind(on_release=self.start_game_sequence)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size='16sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

    def sync_rsvp_box(self, instance, value):
        self.rsvp_bg.pos = (0, 0)
        self.rsvp_bg.size = instance.size
        self.rsvp_border.rectangle = (0, 0, instance.width, instance.height)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        rules = [
            "Focus your eyes inside the yellow reading box",
            "Words will flash rapidly one-by-one (RSVP)",
            "Maintain focus to absorb the short randomized story",
            "Answer the multiple-choice questions correctly to advance",
            "Reading speed increases with each round completed!"
        ]
        overlay = InstructionOverlay("Rapid Reader", rules, self.on_instructions_closed)
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False

    def on_pre_enter(self, *args):
        self.stop_game_engine()
        self.title_label.text = "RAPID READER"
        self.score = 0
        self.round_number = 1
        self.score_label.text = "SCORE: 0"
        self.load_high_score()
        self.hi_score_label.text = f"BEST: {self.high_score}"
        self.wpm_label.text = "SPEED: 200 WPM"
        self.rsvp_label.text = "READY?"
        self.rsvp_container.opacity = 1
        self.mcq_container.opacity = 0
        self.mcq_container.disabled = True
        if self.play_help_row not in self.layout.children:
            self.layout.add_widget(self.play_help_row)
        self.start_btn.text = "START GAME"

    def on_leave(self, *args):
        self.stop_game_engine()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def go_back_to_menu(self, instance):
        self.stop_game_engine()
        self.manager.current = 'menu'

    def load_high_score(self):
        try:
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r', encoding='utf-8') as f:
                    self.high_score = json.load(f).get('rapid_reader_high', 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self):
        try:
            data = {}
            if os.path.exists('save_data.json'):
                with open('save_data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
            data['rapid_reader_high'] = self.high_score
            with open('save_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception:
            pass

    # --- STORY GENERATOR ---
    def generate_random_story(self):
        self.story_variables = {}
        for key, bank in self.word_banks.items():
            self.story_variables[key] = random.choice(bank)

        # Grammar article helpers
        a_adj1 = "an" if self.story_variables['ADJECTIVE_1'][0].lower() in "aeiou" else "a"
        a_adj2 = "an" if self.story_variables['ADJECTIVE_2'][0].lower() in "aeiou" else "a"
        a_adj3 = "an" if self.story_variables['ADJECTIVE_3'][0].lower() in "aeiou" else "a"

        s1 = f"Yesterday, {a_adj1} {self.story_variables['ADJECTIVE_1']} {self.story_variables['SUBJECT_1']} {self.story_variables['VERB_1_PAST']} a {self.story_variables['OBJECT_1']} near the {self.story_variables['LOCATION_1']}."
        s2 = f"Suddenly, {a_adj2} {self.story_variables['ADJECTIVE_2']} {self.story_variables['SUBJECT_2']} {self.story_variables['ADVERB_1']} {self.story_variables['VERB_2_PAST']} them with a {self.story_variables['OBJECT_2']}."
        s3 = f"This caused the {self.story_variables['SUBJECT_1']} to {self.story_variables['VERB_3_BASE']} the {self.story_variables['OBJECT_1']} directly toward the {self.story_variables['LOCATION_2']}."
        s4 = f"Upon reaching the {self.story_variables['LOCATION_2']}, everyone discovered {a_adj3} {self.story_variables['ADJECTIVE_3']} {self.story_variables['OBJECT_3']} hidden inside."
        s5 = f"In the end, the {self.story_variables['SUBJECT_2']} {self.story_variables['VERB_4_PAST']} {self.story_variables['ADVERB_2']} and decided to {self.story_variables['VERB_5_BASE']} until {self.story_variables['TIME_FRAME']}."

        full_text = f"{s1} {s2} {s3} {s4} {s5}"
        self.current_story_words = full_text.split()

    # --- QUESTION GENERATOR ---
    def generate_questions(self):
        possible_questions = [
            {
                'prompt': f"What did the {self.story_variables['SUBJECT_1']} do first?",
                'correct': self.story_variables['VERB_1_PAST'],
                'bank': 'VERB_1_PAST'
            },
            {
                'prompt': f"Where was the {self.story_variables['OBJECT_1']} located at first?",
                'correct': self.story_variables['LOCATION_1'],
                'bank': 'LOCATION_1'
            },
            {
                'prompt': f"What did the {self.story_variables['SUBJECT_2']} use as a tool?",
                'correct': self.story_variables['OBJECT_2'],
                'bank': 'OBJECT_2'
            },
            {
                'prompt': f"Where was the {self.story_variables['OBJECT_1']} sent toward?",
                'correct': self.story_variables['LOCATION_2'],
                'bank': 'LOCATION_2'
            },
            {
                'prompt': f"What hidden item was discovered inside the {self.story_variables['LOCATION_2']}?",
                'correct': self.story_variables['OBJECT_3'],
                'bank': 'OBJECT_3'
            },
            {
                'prompt': f"How long did the {self.story_variables['SUBJECT_2']} decide to {self.story_variables['VERB_5_BASE']}?",
                'correct': self.story_variables['TIME_FRAME'],
                'bank': 'TIME_FRAME'
            }
        ]

        # Select 3-5 questions at random for this round
        q_count = min(3 + (self.round_number // 2), 5)
        selected_templates = random.sample(possible_questions, q_count)

        self.questions_queue = []
        for q_data in selected_templates:
            correct_ans = q_data['correct']
            bank_key = q_data['bank']
            
            # Select 3 distractor choices from the same bank
            distractors = [w for w in self.word_banks[bank_key] if w != correct_ans]
            chosen_distractors = random.sample(distractors, 3)
            
            options = chosen_distractors + [correct_ans]
            random.shuffle(options)

            self.questions_queue.append({
                'prompt': q_data['prompt'],
                'options': options,
                'correct_idx': options.index(correct_ans)
            })

    # --- GAME FLOW & ENGINE ---
    def start_game_sequence(self, instance=None):
        if self.play_help_row in self.layout.children:
            self.layout.remove_widget(self.play_help_row)

        self.game_active = True
        self.mcq_container.opacity = 0
        self.mcq_container.disabled = True
        self.rsvp_container.opacity = 1

        self.generate_random_story()
        self.generate_questions()

        self.countdown_ticks = 3
        self.rsvp_label.text = str(self.countdown_ticks)
        
        if self.timer_event:
            Clock.unschedule(self.timer_event)
        self.timer_event = Clock.schedule_interval(self.handle_countdown_tick, 1.0)

    def handle_countdown_tick(self, dt):
        self.countdown_ticks -= 1
        if self.countdown_ticks > 0:
            self.rsvp_label.text = str(self.countdown_ticks)
        else:
            Clock.unschedule(self.timer_event)
            self.begin_rsvp_reading()

    def begin_rsvp_reading(self):
        self.current_word_idx = 0
        # WPM scales up with round progress (200 WPM, 230 WPM, 260 WPM, etc.)
        wpm = 200 + ((self.round_number - 1) * 30)
        self.wpm_label.text = f"SPEED: {wpm} WPM"
        word_delay = 60.0 / wpm

        self.timer_event = Clock.schedule_interval(self.tick_rsvp_word, word_delay)

    def tick_rsvp_word(self, dt):
        if self.current_word_idx < len(self.current_story_words):
            self.rsvp_label.text = self.current_story_words[self.current_word_idx]
            self.current_word_idx += 1
        else:
            Clock.unschedule(self.timer_event)
            self.rsvp_label.text = ""
            Clock.schedule_once(lambda dt: self.transition_to_questions(), 1.0)

    def transition_to_questions(self):
        self.rsvp_container.opacity = 0
        self.mcq_container.opacity = 1
        self.mcq_container.disabled = False
        self.load_next_question()

    def load_next_question(self):
        if self.questions_queue:
            self.current_question = self.questions_queue.pop(0)
            self.q_prompt_label.text = self.current_question['prompt']

            for i, btn in enumerate(self.option_buttons):
                btn.text = f"{chr(97 + i)})  {self.current_question['options'][i].upper()}"
                btn.background_color = (0, 0.75, 1, 1)
                btn.disabled = False
        else:
            self.trigger_round_complete()

    def handle_answer_selection(self, instance):
        if not self.current_question:
            return

        # Disable buttons during flash feedback
        for btn in self.option_buttons:
            btn.disabled = True

        correct_idx = self.current_question['correct_idx']

        if instance.option_idx == correct_idx:
            trigger_haptic_feedback(0.04)
            instance.background_color = (0.1, 0.8, 0.3, 1)  # Green
            self.score += 5
            self.score_label.text = f"SCORE: {self.score}"
            
            if self.score > self.high_score:
                self.high_score = self.score
                self.hi_score_label.text = f"BEST: {self.high_score}"
                self.save_high_score()

            Clock.schedule_once(lambda dt: self.load_next_question(), 0.8)
        else:
            trigger_haptic_feedback(0.12)
            instance.background_color = (0.85, 0.15, 0.15, 1)  # Red Flash
            self.option_buttons[correct_idx].background_color = (0.1, 0.8, 0.3, 1)  # Highlight Green
            
            Clock.schedule_once(lambda dt: self.load_next_question(), 1.2)

    def trigger_round_complete(self):
        self.round_number += 1
        self.mcq_container.opacity = 0
        self.mcq_container.disabled = True
        self.rsvp_container.opacity = 1
        self.rsvp_label.text = "ROUND COMPLETE!"
        
        self.start_btn.text = f"START GAME {self.round_number}"
        if self.play_help_row not in self.layout.children:
            self.layout.add_widget(self.play_help_row)

    def stop_game_engine(self):
        self.game_active = False
        if self.timer_event:
            Clock.unschedule(self.timer_event)
            self.timer_event = None
        self.rsvp_label.text = "READY?"
        self.rsvp_container.opacity = 1
        self.mcq_container.opacity = 0
        self.mcq_container.disabled = True
        
class HalloweenGameScreen(Screen):
    """
    GRAVEYARD SHIFT (WHACK-A-GHOUL) - PHASE 3: ENEMY VARIETY & VISUAL METERS
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.score = 0
        self.high_score = 0
        self.game_active = False
        
        # 12:00 AM to 6:00 AM Shift Clock
        self.shift_seconds_left = 60.0
        
        # Loose Ghouls & Panic State
        self.loose_ghoul_count = 0
        self.panic_level = 0.0  # 0.0 to 100.0
        self.lantern_snuffed = False
        self.jumpscare_active = False
        self.jumpscare_timer = 0.0
        
        # Flashbang Effect State (from Wisp taps)
        self.flashbang_alpha = 0.0
        
        # Sliding Lantern Properties
        self.lantern_y_pct = 0.5
        self.lantern_dir = 1
        self.lantern_size = Scale.min_dim(0.12)
        
        # 3x3 Grave Grid State
        self.graves = []
        self.spawn_timer = 0.0
        self.spawn_interval = 1.2
        self.game_event = None

        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        # Base Night Grass Layer
        with self.canvas.before:
            Color(0.04, 0.10, 0.06, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.load_high_score()
        
        def apply_sharp_filtering(texture):
            if texture:
                texture.mag_filter = 'nearest'
                texture.min_filter = 'nearest'

        # --- HUD ELEMENTS ---
        self.title_label = Label(
            text="GRAVEYARD SHIFT", 
            font_size=Scale.font(18), 
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 0.5, 0, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.95}
        )
        self.layout.add_widget(self.title_label)

        self.time_label = Label(
            text="SHIFT: 12:00 AM", 
            font_size=Scale.font(9), 
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0, 0.75, 1, 1), 
            pos_hint={'center_x': 0.22, 'center_y': 0.89}
        )
        self.layout.add_widget(self.time_label)

        self.score_label = Label(
            text="WHACKS: 0", 
            font_size=Scale.font(9), 
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 1, 1, 1), 
            pos_hint={'center_x': 0.50, 'center_y': 0.89}
        )
        self.layout.add_widget(self.score_label)

        self.hi_score_label = Label(
            text=f"BEST: {self.high_score}", 
            font_size=Scale.font(9), 
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 0.84, 0, 1), 
            pos_hint={'center_x': 0.78, 'center_y': 0.89}
        )
        self.layout.add_widget(self.hi_score_label)

        # Labels for visual meter indicators
        self.ghoul_meter_title = Label(
            text="LOOSE", 
            font_size=Scale.font(7), 
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.2, 0.8, 0.2, 1), 
            pos_hint={'center_x': 0.28, 'center_y': 0.85}
        )
        self.layout.add_widget(self.ghoul_meter_title)

        self.panic_meter_title = Label(
            text="PANIC", 
            font_size=Scale.font(7), 
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 0.8, 0, 1), 
            pos_hint={'center_x': 0.72, 'center_y': 0.85}
        )
        self.layout.add_widget(self.panic_meter_title)

        self.back_btn = Button(
            text="< MENU", 
            font_size=Scale.font(10), 
            font_name='assets/fonts/ARCADE_N.TTF', 
            color=(1, 1, 1, 1),
            size_hint=(0.22, 0.05), 
            pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='', 
            background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        self.play_help_row = BoxLayout(
            orientation='horizontal',
            spacing=dp(10),
            size_hint=(0.9, 0.08),
            pos_hint={'center_x': 0.5, 'center_y': 0.08}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START SHIFT", 
            font_size=Scale.font(14), 
            font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.04, 0.06, 0.17, 1), 
            size_hint_x=0.8,
            background_normal='', 
            background_color=(1, 0.5, 0, 1)
        )
        self.start_btn.bind(on_release=self.start_game)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", 
            font_size=Scale.font(14), 
            font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', 
            background_color=(0, 0.5, 0.8, 1), 
            color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

        self.build_grave_grid_state()

    # --- INSTRUCTIONS OVERLAY ---
    # --- INSTRUCTIONS OVERLAY FIX ---
    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.back_btn.disabled = True
        
        # Hide the canvas objects so they don't bleed through the overlay
        self.canvas.remove_group('game_world')
        
        game_name = "Graveyard Shift"
        rules = [
            "Survive from 12:00 AM to 6:00 AM.",
            "Green Ghouls = 1 tap. Armored Skeletons = 2 taps.",
            "AVOID Yellow Wisps! Tapping causes blinding flashbangs.",
            "3 missed ghouls snuff out lantern! Relight before Panic reaches 100%!"
        ]
        
        overlay = InstructionOverlay(
            game_name=game_name,
            rules_list=rules,
            close_callback=self.on_instructions_closed
        )
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.back_btn.disabled = False
        # Redraw the graveyard canvas elements now that instructions are dismissed
        self.draw_graveyard_canvas()

    def build_grave_grid_state(self):
        self.graves = []
        for row in range(3):
            for col in range(3):
                self.graves.append({
                    'row': row,
                    'col': col,
                    'ghoul_active': False,
                    'ghoul_timer': 0.0,
                    'type': 'ghoul',  # 'ghoul', 'skeleton', 'wisp'
                    'health': 1
                })

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        apply_theme_background(self)
        self.draw_graveyard_canvas()

    def draw_graveyard_canvas(self):
        self.canvas.remove_group('game_world')
        if not self.graves:
            return

        grid_center_x = Window.width * 0.5
        grid_center_y = Window.height * 0.48
        spacing_x = Scale.width_pct(0.28)
        spacing_y = Scale.height_pct(0.17)

        grave_w = Scale.min_dim(0.20)
        grave_h = Scale.min_dim(0.12)
        tomb_w = grave_w * 0.60
        tomb_h = grave_h * 0.70
        ghoul_radius = grave_w * 0.35

        with self.canvas:
            # 1. GRAVEYARD GRID (Graves, Tombstones, Enemies)
            for g in self.graves:
                col_offset = (g['col'] - 1) * spacing_x
                row_offset = (g['row'] - 1) * spacing_y
                
                cx = grid_center_x + col_offset
                cy = grid_center_y + row_offset

                g['cx'] = cx
                g['cy'] = cy
                g['w'] = grave_w
                g['h'] = grave_h

                # Light Gray Tombstone
                Color(0.70, 0.72, 0.75, 1, group='game_world')
                tomb_x = cx - (tomb_w / 2)
                tomb_y = cy + (grave_h / 2) - dp(2)
                Rectangle(pos=(tomb_x, tomb_y), size=(tomb_w, tomb_h), group='game_world')

                # Active Enemies
                if g['ghoul_active']:
                    gx = cx - ghoul_radius
                    gy = cy - ghoul_radius + (grave_h * 0.25)
                    
                    if g['type'] == 'ghoul':
                        # Green Ghoul Sprite / Circle
                        #Color(0.2, 0.9, 0.2, 1, group='game_world')
                        #Ellipse(pos=(gx, gy), size=(ghoul_radius * 2, ghoul_radius * 2), group='game_world')
                        # ATLAS SPRITE PLACEHOLDER:
                        Rectangle(source='atlas://assets/images/game_sprites/ghoul', pos=(gx, gy+20), size=(ghoul_radius*2, ghoul_radius*2), group='game_world')

                    elif g['type'] == 'skeleton':
                        # White Armored Skeleton Triangle
                        #Color(0.9, 0.9, 0.9, 1, group='game_world')
                        # Draw triangle mesh representation
                        #p1 = (cx, gy + ghoul_radius * 2)
                        #p2 = (gx, gy)
                        #p3 = (gx + ghoul_radius * 2, gy)
                        #Mesh(vertices=[p1[0], p1[1], 0, 0, p2[0], p2[1], 0, 0, p3[0], p3[1], 0, 0], 
                             #indices=[0, 1, 2], mode='triangles', group='game_world')
                        # ATLAS SPRITE PLACEHOLDER:
                        Rectangle(source='atlas://assets/images/game_sprites/skeleton', pos=(gx, gy+20), size=(ghoul_radius*2, ghoul_radius*2), group='game_world')

                    elif g['type'] == 'wisp':
                        # Yellow Will-o'-the-Wisp Circle
                        Color(1.0, 0.85, 0.1, 1, group='game_world')
                        #Ellipse(pos=(gx, gy), size=(ghoul_radius * 2, ghoul_radius * 2), group='game_world')
                        # ATLAS SPRITE PLACEHOLDER:
                        Rectangle(source='atlas://assets/images/game_sprites/wisp', pos=(gx, gy+20), size=(ghoul_radius*2, ghoul_radius*2), group='game_world')

                # Dark Brown Dug Grave Rect
                Color(0.22, 0.12, 0.05, 1, group='game_world')
                Rectangle(pos=(cx - grave_w / 2, cy - grave_h / 2), size=(grave_w, grave_h), group='game_world')

            # 2. HORIZONTAL HUD BARS (Loose Ghouls & Panic)
            bar_w = Scale.width_pct(0.20)
            bar_h = dp(12)

            # A) Loose Ghoul Bar (Bright Green Border, Dark Green Fill)
            ghoul_bar_x = Window.width * 0.28 - bar_w / 2
            ghoul_bar_y = Window.height * 0.81
            Color(0.2, 0.9, 0.2, 1, group='game_world')  # Bright Green Border
            Rectangle(pos=(ghoul_bar_x - dp(2), ghoul_bar_y - dp(2)), size=(bar_w + dp(4), bar_h + dp(4)), group='game_world')
            Color(0.05, 0.25, 0.05, 1, group='game_world')  # Dark Green Background
            Rectangle(pos=(ghoul_bar_x, ghoul_bar_y), size=(bar_w, bar_h), group='game_world')
            
            fill_ratio = self.loose_ghoul_count / 3.0
            if fill_ratio > 0:
                Color(0.2, 0.8, 0.2, 1, group='game_world')  # Dark Green Fill
                Rectangle(pos=(ghoul_bar_x, ghoul_bar_y), size=(bar_w * fill_ratio, bar_h), group='game_world')

            # B) Panic Meter Bar (Yellow Border, Orange Fill)
            panic_bar_x = Window.width * 0.72 - bar_w / 2
            panic_bar_y = Window.height * 0.81
            Color(1.0, 0.85, 0.1, 1, group='game_world')  # Yellow Border
            Rectangle(pos=(panic_bar_x - dp(2), panic_bar_y - dp(2)), size=(bar_w + dp(4), bar_h + dp(4)), group='game_world')
            Color(0.2, 0.1, 0.0, 1, group='game_world')  # Dark Background
            Rectangle(pos=(panic_bar_x, panic_bar_y), size=(bar_w, bar_h), group='game_world')
            
            panic_ratio = min(1.0, max(0.0, self.panic_level / 100.0))
            if panic_ratio > 0:
                Color(1.0, 0.4, 0.0, 1, group='game_world')  # Pumpkin Orange Fill
                Rectangle(pos=(panic_bar_x, panic_bar_y), size=(bar_w * panic_ratio, bar_h), group='game_world')

            # 3. SLIDING LANTERN
            if self.lantern_snuffed:
                l_size = self.lantern_size
                lx = Window.width - l_size - dp(10)
                ly = self.lantern_y_pct * (Window.height - l_size)

                self.lantern_rect = (lx, ly, l_size, l_size)

                Color(0.2, 0.2, 0.2, 1, group='game_world')
                Rectangle(pos=(lx, ly), size=(l_size, l_size), group='game_world')

                Color(1.0, 0.9, 0.1, 1, group='game_world')
                glow_margin = l_size * 0.2
                Ellipse(
                    pos=(lx + glow_margin, ly + glow_margin), 
                    size=(l_size - glow_margin * 2, l_size - glow_margin * 2), 
                    group='game_world'
                )

                # Blackout Overlay
                Color(0, 0, 0, 0.85, group='game_world')
                Rectangle(pos=(0, 0), size=Window.size, group='game_world')

            # 4. FLASHBANG OVERLAY (Wisp Penalty)
            if self.flashbang_alpha > 0.01:
                Color(1, 1, 1, self.flashbang_alpha, group='game_world')
                Rectangle(pos=(0, 0), size=Window.size, group='game_world')

            # 5. JUMPSCARE OVERLAY
            if self.jumpscare_active:
                Color(1, 1, 1, 1, group='game_world')
                Rectangle(
                    source='atlas://assets/images/game_sprites/jumpscare',
                    pos=(0, 0),
                    size=Window.size,
                    group='game_world'
                )

    # --- TOUCH & WHACK INTERACTION ---
    def on_touch_down(self, touch):
        if self.back_btn.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        if not self.game_active or self.jumpscare_active:
            return super().on_touch_down(touch)

        # 1. Tap Obscured Lantern
        if self.lantern_snuffed and hasattr(self, 'lantern_rect'):
            lx, ly, lw, lh = self.lantern_rect
            if lx <= touch.x <= lx + lw and ly <= touch.y <= ly + lh:
                self.lantern_snuffed = False
                trigger_haptic_feedback(0.08)
                self.draw_graveyard_canvas()
                return True

        # 2. Whack Enemies
        for g in self.graves:
            if g['ghoul_active']:
                dist_sq = (touch.x - g['cx'])**2 + (touch.y - g['cy'])**2
                click_radius = (g['w'] / 2) * 1.2
                
                if dist_sq <= (click_radius ** 2):
                    if g['type'] == 'wisp':
                        # TRAP! Trigger Flashbang
                        g['ghoul_active'] = False
                        self.flashbang_alpha = 1.0
                        trigger_haptic_feedback(0.15)
                        self.draw_graveyard_canvas()
                        return True

                    elif g['type'] == 'skeleton':
                        # Armored Skeleton: Requires 2 Taps
                        g['health'] -= 1
                        trigger_haptic_feedback(0.04)
                        if g['health'] <= 0:
                            g['ghoul_active'] = False
                            self.add_score(1)
                        self.draw_graveyard_canvas()
                        return True

                    else:
                        # Standard Ghoul: 1 Tap
                        g['ghoul_active'] = False
                        self.add_score(1)
                        trigger_haptic_feedback(0.06)
                        self.draw_graveyard_canvas()
                        return True

        return super().on_touch_down(touch)

    def add_score(self, amount):
        self.score += amount
        self.score_label.text = f"WHACKS: {self.score}"
        if self.score > self.high_score:
            self.high_score = self.score
            self.hi_score_label.text = f"BEST: {self.high_score}"
            self.save_high_score()

    # --- ENGINE LOOP ---
    def start_game(self, instance=None):
        if self.play_help_row in self.layout.children:
            self.layout.remove_widget(self.play_help_row)

        self.score = 0
        self.shift_seconds_left = 60.0
        self.spawn_timer = 0.0
        self.spawn_interval = 1.0
        self.loose_ghoul_count = 0
        self.panic_level = 0.0
        self.flashbang_alpha = 0.0
        self.lantern_snuffed = False
        self.jumpscare_active = False

        for g in self.graves:
            g['ghoul_active'] = False
            g['ghoul_timer'] = 0.0

        self.score_label.text = "WHACKS: 0"
        self.time_label.text = "SHIFT: 12:00 AM"
        self.title_label.text = "SURVIVE THE SHIFT!"
        self.title_label.color = (1, 0.5, 0, 1)

        self.game_active = True
        self.draw_graveyard_canvas()

        if self.game_event:
            Clock.unschedule(self.game_event)
        self.game_event = Clock.schedule_interval(self.game_loop_tick, 1.0 / 60.0)

    def game_loop_tick(self, dt):
        if not self.game_active:
            return

        if self.jumpscare_active:
            self.jumpscare_timer -= dt
            if self.jumpscare_timer <= 0:
                self.trigger_game_over()
            return

        # 1. Update Shift Clock
        self.shift_seconds_left -= dt
        if self.shift_seconds_left <= 0:
            self.trigger_shift_complete()
            return

        elapsed = 60.0 - self.shift_seconds_left
        hour = int((elapsed / 60.0) * 6)
        display_hour = 12 if hour == 0 else hour
        self.time_label.text = f"SHIFT: {display_hour}:00 AM"

        # 2. Fade Flashbang
        if self.flashbang_alpha > 0.0:
            self.flashbang_alpha = max(0.0, self.flashbang_alpha - dt * 1.0)  # Fades over 1 sec

        # 3. Lantern & Panic Depletion Logic
        if self.lantern_snuffed:
            self.lantern_y_pct += self.lantern_dir * dt * 0.45
            if self.lantern_y_pct >= 0.8:
                self.lantern_y_pct = 0.8
                self.lantern_dir = -1
            elif self.lantern_y_pct <= 0.15:
                self.lantern_y_pct = 0.15
                self.lantern_dir = 1

            self.panic_level += dt * 35.0
            if self.panic_level >= 100.0:
                self.trigger_jumpscare()
                return
        else:
            # Panic depletes slowly when lantern is lit
            if self.panic_level > 0.0:
                self.panic_level = max(0.0, self.panic_level - dt * 12.0)

        # 4. Update Enemy Lifespans
        for g in self.graves:
            if g['ghoul_active']:
                g['ghoul_timer'] -= dt
                if g['ghoul_timer'] <= 0:
                    g['ghoul_active'] = False
                    # Wisps do NOT increment loose ghoul counter when missed
                    if g['type'] != 'wisp':
                        self.on_ghoul_escaped()

        # 5. Spawns
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            self.try_spawn_ghoul()

        self.draw_graveyard_canvas()

    def on_ghoul_escaped(self):
        self.loose_ghoul_count += 1
        
        if self.loose_ghoul_count >= 3:
            self.loose_ghoul_count = 0
            self.lantern_snuffed = True
            trigger_haptic_feedback(0.10)

    def try_spawn_ghoul(self):
        inactive_graves = [g for g in self.graves if not g['ghoul_active']]
        if inactive_graves:
            chosen_grave = random.choice(inactive_graves)
            chosen_grave['ghoul_active'] = True
            
            # Pick random enemy type (60% Ghoul, 25% Skeleton, 15% Wisp)
            roll = random.random()
            if roll < 0.60:
                chosen_grave['type'] = 'ghoul'
                chosen_grave['health'] = 1
            elif roll < 0.85:
                chosen_grave['type'] = 'skeleton'
                chosen_grave['health'] = 2
            else:
                chosen_grave['type'] = 'wisp'
                chosen_grave['health'] = 1

            base_lifespan = max(0.8, 1.8 - ((60.0 - self.shift_seconds_left) / 60.0) * 0.8)
            chosen_grave['ghoul_timer'] = base_lifespan

    # --- JUMPSCARE & GAME OVER ---
    def trigger_jumpscare(self):
        self.jumpscare_active = True
        self.jumpscare_timer = 1.0
        #trigger_haptic_feedback(0.50)
        
        SoundLoader.load('assets/audios/jumpscare.ogg').play()

        self.draw_graveyard_canvas()

    def trigger_game_over(self):
        self.stop_game_engine()
        self.title_label.text = "SHIFT FAILED!"
        self.title_label.color = (1, 0.1, 0.1, 1)
        self.start_btn.text = "RETRY SHIFT"

        if self.play_help_row not in self.layout.children:
            self.layout.add_widget(self.play_help_row)

    def trigger_shift_complete(self):
        self.stop_game_engine()
        trigger_haptic_feedback(0.12)
        self.title_label.text = "SURVIVED THE SHIFT!"
        self.title_label.color = (0.1, 0.9, 0.3, 1)
        self.start_btn.text = "NEXT SHIFT"

        if self.play_help_row not in self.layout.children:
            self.layout.add_widget(self.play_help_row)

    def stop_game_engine(self):
        self.game_active = False
        self.lantern_snuffed = False
        self.jumpscare_active = False
        self.flashbang_alpha = 0.0
        
        if self.game_event:
            Clock.unschedule(self.game_event)
            self.game_event = None
            
        for g in self.graves:
            g['ghoul_active'] = False
            
        self.draw_graveyard_canvas()

    def on_pre_enter(self, *args):
        apply_theme_background(self)
        self.stop_game_engine()
        self.title_label.text = "GRAVEYARD SHIFT"
        self.title_label.color = (1, 0.5, 0, 1)
        self.time_label.text = "SHIFT: 12:00 AM"
        self.score_label.text = "WHACKS: 0"
        self.loose_ghoul_count = 0
        self.panic_level = 0.0
        self.load_high_score()
        self.hi_score_label.text = f"BEST: {self.high_score}"
        
        if self.play_help_row not in self.layout.children:
            self.layout.add_widget(self.play_help_row)
        self.play_help_row.disabled = False

    def on_leave(self, *args):
        self.stop_game_engine()
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)

    def go_back_to_menu(self, instance):
        self.stop_game_engine()
        self.manager.current = 'menu'

    def load_high_score(self):
        self.high_score = web_load_game_data('graveyard_shift_high', 0)

    def save_high_score(self):
        web_save_game_data('graveyard_shift_high', self.high_score)
        
class ChristmasGameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_running = False
        self.score = 0
        self.high_score = 0
        self.difficulties = ['EASY', 'NORMAL', 'HARD']
        self.current_diff_idx = 1  # Default to NORMAL

        # Sleigh Dimensions & Altitude Logic
        self.sleigh_w = Scale.min_dim(0.18)
        self.sleigh_h = Scale.min_dim(0.10)
        self.sleigh_x = Window.width * 0.25
        self.sleigh_y = Window.height * 0.75  # Spawns at 75% height
        
        # Altitude Bounds (Upper half: 50% to 95%)
        self.min_sleigh_y = Window.height * 0.50
        self.max_sleigh_y = Window.height * 0.95 - self.sleigh_h

        # Missile Engine (Sky)
        self.missiles = []
        self.missile_w = Scale.min_dim(0.12)
        self.missile_h = Scale.min_dim(0.04)

        # Houses & Chimneys Engine (Ground)
        self.houses = []
        self.house_w = Scale.min_dim(0.24)
        self.house_h = Scale.min_dim(0.20)

        # Dropped Projectiles Engine (Presents / Coal)
        self.dropped_items = []
        self.item_size = Scale.min_dim(0.04)

        # Timers & Loops
        self.update_event = None
        self.spawn_missile_event = None
        self.spawn_house_event = None
        self.touch_active = False

        self.layout = RelativeLayout()
        self.add_widget(self.layout)
        
        self.game_canvas_group = InstructionGroup()
        self.canvas.add(self.game_canvas_group)

        # Dark Cosmic Background
        with self.canvas.before:
            Color(0.04, 0.06, 0.17, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        # UI Headers
        self.title_label = Label(
            text="SLEIGH DROP", font_size=Scale.font(28), font_name='assets/fonts/ARCADE_N.TTF',
            color=(0.85, 0.95, 1.0, 1), pos_hint={'center_x': 0.5, 'center_y': 0.90}
        )
        self.layout.add_widget(self.title_label)

        self.score_label = Label(
            text="SCORE: 0  |  BEST: 0", font_size=Scale.font(14), font_name='assets/fonts/ARCADE_N.TTF',
            color=(1, 1, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.82}
        )
        self.layout.add_widget(self.score_label)

        # Back Button
        self.back_btn = Button(
            text="< MENU", font_size=Scale.font(15), font_name='assets/fonts/ARCADE_N.TTF', color=(1, 1, 1, 1),
            size_hint=(0.25, 0.05), pos_hint={'x': 0.0, 'top': 1.0},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1)
        )
        self.back_btn.bind(on_release=self.go_back_to_menu)
        self.layout.add_widget(self.back_btn)

        # Action Controls Row (Menu)
        self.play_help_row = BoxLayout(
            orientation='horizontal', spacing=dp(10),
            size_hint=(0.9, 0.1), pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )
        self.layout.add_widget(self.play_help_row)

        self.start_btn = Button(
            text="START GAME", font_size=Scale.font(25), font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0.75, 0.1, 0.1, 1), color=(1, 1, 1, 1),
            size_hint_x=0.8
        )
        self.start_btn.bind(on_release=self.start_game)
        self.play_help_row.add_widget(self.start_btn)

        self.help_btn = Button(
            text="?", font_size=Scale.font(16), font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0.1, 0.55, 0.2, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        self.play_help_row.add_widget(self.help_btn)

        # Difficulty Row
        self.diff_row = BoxLayout(
            orientation='horizontal', spacing=dp(10),
            size_hint=(0.9, None), height=dp(45),
            pos_hint={'center_x': 0.5, 'center_y': 0.1}
        )
        self.layout.add_widget(self.diff_row)

        self.prev_diff_btn = Button(
            text="<", font_name='assets/fonts/ARCADE_N.TTF', font_size=Scale.font(16), size_hint_x=0.2,
            background_normal='', background_color=(0.75, 0.1, 0.1, 0.4), color=(1, 1, 1, 1)
        )
        self.prev_diff_btn.bind(on_release=lambda x: self.cycle_difficulty(-1))
        self.diff_row.add_widget(self.prev_diff_btn)

        self.diff_label = Label(
            text="NORMAL", font_name='assets/fonts/ARCADE_N.TTF', font_size=Scale.font(16),
            color=(1, 1, 1, 1), halign='center'
        )
        self.diff_row.add_widget(self.diff_label)

        self.next_diff_btn = Button(
            text=">", font_name='assets/fonts/ARCADE_N.TTF', font_size=Scale.font(16), size_hint_x=0.2,
            background_normal='', background_color=(0.75, 0.1, 0.1, 0.4), color=(1, 1, 1, 1)
        )
        self.next_diff_btn.bind(on_release=lambda x: self.cycle_difficulty(1))
        self.diff_row.add_widget(self.next_diff_btn)

        # --- PHASE 2.2: DROP BUTTONS (Lower Right Zone) ---
        self.drop_btn_container = BoxLayout(
            orientation='vertical', spacing=dp(12),
            size_hint=(None, None), size=(dp(65), dp(135)),
            pos_hint={'right': 0.95, 'top': 0.48},
            opacity=0, disabled=True
        )
        self.layout.add_widget(self.drop_btn_container)

        # Top Button: Present (Red circle with Green Square icon)
        self.btn_present = Button(
            background_normal='', background_color=(0.75, 0.1, 0.1, 0.85),
            size_hint=(1, 0.5)
        )
        self.btn_present.bind(on_release=lambda x: self.drop_item('present'))
        
        # Present Icon Layout inside button
        with self.btn_present.canvas.after:
            Color(0.1, 0.75, 0.2, 1) # Green square
            self.present_icon_rect = Rectangle()
        self.btn_present.bind(pos=self.update_btn_icons, size=self.update_btn_icons)
        self.drop_btn_container.add_widget(self.btn_present)

        # Bottom Button: Coal (Red circle with Black Circle icon)
        self.btn_coal = Button(
            background_normal='', background_color=(0.75, 0.1, 0.1, 0.85),
            size_hint=(1, 0.5)
        )
        self.btn_coal.bind(on_release=lambda x: self.drop_item('coal'))

        # Coal Icon Layout inside button
        with self.btn_coal.canvas.after:
            Color(0.1, 0.1, 0.1, 1) # Black circle
            self.coal_icon_ellipse = Ellipse()
        self.btn_coal.bind(pos=self.update_btn_icons, size=self.update_btn_icons)
        self.drop_btn_container.add_widget(self.btn_coal)

        self.load_high_score()

    def update_btn_icons(self, *args):
        # Center Present Icon
        pw, ph = dp(20), dp(20)
        px = self.btn_present.x + (self.btn_present.width - pw) / 2
        py = self.btn_present.y + (self.btn_present.height - ph) / 2
        self.present_icon_rect.pos = (px, py)
        self.present_icon_rect.size = (pw, ph)

        # Center Coal Icon
        cw, ch = dp(20), dp(20)
        cx = self.btn_coal.x + (self.btn_coal.width - cw) / 2
        cy = self.btn_coal.y + (self.btn_coal.height - ch) / 2
        self.coal_icon_ellipse.pos = (cx, cy)
        self.coal_icon_ellipse.size = (cw, ch)

    def show_instructions_overlay(self, instance):
        self.play_help_row.disabled = True
        self.diff_row.disabled = True
        self.back_btn.disabled = True

        rules = [
            "Drag left side up/down to control Santa's altitude and dodge missiles",
            "NICE houses (Green roofs) want PRESENTS (+10 pts)",
            "NAUGHTY houses (Red roofs) want COAL (+10 pts)",
            "Wrong drops deduct 10 points!"
        ]

        overlay = InstructionOverlay(
            game_name="Sleigh Drop",
            rules_list=rules,
            close_callback=self.on_instructions_closed
        )
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        self.play_help_row.disabled = False
        self.diff_row.disabled = False
        self.back_btn.disabled = False

    def on_pre_enter(self, *args):
        apply_theme_background(self)
        self.update_difficulty_ui()
        self.reset_menu_ui()
        
    def reset_menu_ui(self):
        """Resets screen UI and forces canvas render when entering or returning."""
        self.stop_engine()
        self.game_running = False
        
        # Restore action buttons & hide drop buttons
        self.play_help_row.opacity = 1
        self.play_help_row.disabled = False
        self.diff_row.opacity = 1
        self.diff_row.disabled = False
        
        self.drop_btn_container.opacity = 0
        self.drop_btn_container.disabled = True
        
        # Reset sleigh altitude & clear active entities
        self.sleigh_y = Window.height * 0.75
        self.missiles = []
        self.houses = []
        self.dropped_items = []
        
        # Redraw canvas after UI state settles
        Clock.schedule_once(lambda dt: self.draw_game_canvas(), 0)

    def on_leave(self, *args):
        self.stop_engine()

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.sleigh_w = Scale.min_dim(0.18)
        self.sleigh_h = Scale.min_dim(0.10)
        self.sleigh_x = Window.width * 0.25
        self.min_sleigh_y = Window.height * 0.50
        self.max_sleigh_y = Window.height * 0.95 - self.sleigh_h

        self.house_w = Scale.min_dim(0.48)
        self.house_h = Scale.min_dim(0.40)
        self.item_size = Scale.min_dim(0.04)

        if not self.game_running:
            self.sleigh_y = Window.height * 0.75

        # Always trigger canvas draw on background updates
        Clock.schedule_once(lambda dt: self.draw_game_canvas(), 0)

    def cycle_difficulty(self, direction):
        if self.game_running:
            return
        self.current_diff_idx = (self.current_diff_idx + direction) % len(self.difficulties)
        self.update_difficulty_ui()

    def update_difficulty_ui(self):
        mode = self.difficulties[self.current_diff_idx]
        self.diff_label.text = mode
        self.load_high_score()
        self.score_label.text = f"SCORE: {self.score}  |  BEST: {self.high_score}"

    def load_high_score(self):
        mode = self.difficulties[self.current_diff_idx].lower()
        self.high_score = web_load_game_data(f'sleigh_drop_{mode}_high', 0)

    def save_high_score(self):
        mode = self.difficulties[self.current_diff_idx].lower()
        web_save_game_data(f'sleigh_drop_{mode}_high', self.high_score)

    def go_back_to_menu(self, instance=None):
        self.stop_engine()
        self.reset_menu_ui()  # Ensure clean slate when leaving
        self.manager.current = 'menu'

    def start_game(self, instance=None):
        self.stop_engine()
        self.score = 0
        self.sleigh_y = Window.height * 0.75
        self.missiles = []
        self.houses = []
        self.dropped_items = []

        self.play_help_row.opacity = 0
        self.play_help_row.disabled = True
        self.diff_row.opacity = 0
        self.diff_row.disabled = True

        # Activate Drop Action Buttons
        self.drop_btn_container.opacity = 1
        self.drop_btn_container.disabled = False

        self.game_running = True
        self.score_label.text = f"SCORE: 0  |  BEST: {self.high_score}"

        mode = self.difficulties[self.current_diff_idx]
        missile_rate = 1.8 if mode == 'EASY' else (1.3 if mode == 'NORMAL' else 0.9)
        house_rate = 1.2  # Doubled spawn rate (previously 2.4s)

        self.spawn_missile(0)
        self.spawn_house(0)

        self.update_event = Clock.schedule_interval(self.update_physics, 1.0 / 60.0)
        self.spawn_missile_event = Clock.schedule_interval(self.spawn_missile, missile_rate)
        self.spawn_house_event = Clock.schedule_interval(self.spawn_house, house_rate)

    def spawn_missile(self, dt):
        if not self.game_running:
            return

        min_y = Window.height * 0.50
        max_y = Window.height * 0.92 - self.missile_h
        spawn_y = random.uniform(min_y, max_y)

        mode = self.difficulties[self.current_diff_idx]
        base_speed = Scale.vel_w(5.0) if mode == 'EASY' else (Scale.vel_w(7.0) if mode == 'NORMAL' else Scale.vel_w(9.0))

        self.missiles.append({
            'x': Window.width,
            'y': spawn_y,
            'speed': base_speed + random.uniform(-Scale.vel_w(0.5), Scale.vel_w(1.0))
        })

    def spawn_house(self, dt):
        if not self.game_running:
            return

        mode = self.difficulties[self.current_diff_idx]
        base_house_speed = Scale.vel_w(3.0) if mode == 'EASY' else (Scale.vel_w(4.2) if mode == 'NORMAL' else Scale.vel_w(5.4))

        chimney_side = random.choice(['left', 'right'])
        house_type = random.choice(['nice', 'naughty'])

        self.houses.append({
            'x': Window.width,
            'y': 0,
            'speed': base_house_speed,
            'chimney_side': chimney_side,
            'type': house_type
        })

    def drop_item(self, item_type):
        if not self.game_running:
            return

        # Originates from sleigh center, drops straight down (vx = 0)
        start_x = self.sleigh_x + (self.sleigh_w / 2) - (self.item_size / 2)
        start_y = self.sleigh_y

        self.dropped_items.append({
            'x': start_x,
            'y': start_y,
            'vx': 0,                        # Zero forward momentum
            'vy': -Scale.vel_h(4.0),        # Straight downward gravity pull
            'type': item_type,
            'size': self.item_size
        })

    def on_touch_down(self, touch):
        if self.back_btn.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        if self.game_running:
            if self.drop_btn_container.collide_point(*touch.pos):
                return super().on_touch_down(touch)

            # Touch anywhere in the left half triggers sleigh altitude control
            if touch.x <= Window.width * 0.50:
                self.touch_active = True
                self.update_sleigh_altitude(touch.y)
                return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.game_running and self.touch_active:
            if touch.x <= Window.width * 0.50:
                self.update_sleigh_altitude(touch.y)
                return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        self.touch_active = False
        return super().on_touch_up(touch)

    def update_sleigh_altitude(self, touch_y):
        target_y = touch_y - (self.sleigh_h / 2)
        self.sleigh_y = max(self.min_sleigh_y, min(self.max_sleigh_y, target_y))

    def update_physics(self, dt):
        if not self.game_running:
            return

        # 1. Update Missiles
        for m in self.missiles[:]:
            m['x'] -= m['speed'] * (dt * 60.0)

            if self.check_sleigh_collision(m):
                trigger_haptic_feedback(0.12)
                self.game_over()
                return

            if m['x'] < -self.missile_w:
                self.missiles.remove(m)

        # 2. Update Houses
        for h in self.houses[:]:
            h['x'] -= h['speed'] * (dt * 60.0)

            total_house_width = self.house_w + Scale.min_dim(0.06)
            if h['x'] < -total_house_width:
                self.houses.remove(h)

        # 3. Update Dropped Items & Check Chimney Collisions
        gravity = Scale.vel_h(0.25)
        for item in self.dropped_items[:]:
            item['x'] += item['vx'] * (dt * 60.0)
            item['y'] += item['vy'] * (dt * 60.0)
            item['vy'] -= gravity * (dt * 60.0)  # Gravity acceleration

            # Check Chimney Collision
            hit_chimney = False
            for h in self.houses:
                if self.check_item_chimney_collision(item, h):
                    hit_chimney = True
                    is_nice = (h['type'] == 'nice')
                    is_present = (item['type'] == 'present')

                    # RULE: Present + Nice (+10) | Coal + Naughty (+10) | Mismatch (-10)
                    if (is_present and is_nice) or (not is_present and not is_nice):
                        self.score += 10
                        trigger_haptic_feedback(0.05)
                    else:
                        self.score = max(0, self.score - 10)
                        trigger_haptic_feedback(0.15)

                    if self.score > self.high_score:
                        self.high_score = self.score
                    self.score_label.text = f"SCORE: {self.score}  |  BEST: {self.high_score}"
                    break

            if hit_chimney or item['y'] < 0 or item['x'] > Window.width:
                self.dropped_items.remove(item)

        self.draw_game_canvas()

    def check_sleigh_collision(self, missile):
        s_left, s_right = self.sleigh_x, self.sleigh_x + self.sleigh_w
        s_bottom, s_top = self.sleigh_y, self.sleigh_y + self.sleigh_h

        m_left, m_right = missile['x'], missile['x'] + self.missile_w
        m_bottom, m_top = missile['y'], missile['y'] + self.missile_h

        return (s_left < m_right and s_right > m_left and
                s_bottom < m_top and s_top > m_bottom)

    def check_item_chimney_collision(self, item, house):
        hx, hy = house['x'], house['y']
        hw, hh = self.house_w, self.house_h
        roof_h = hh * 0.50

        # Scaled chimney and lip target bounds
        chimney_w = hw * 0.18
        chimney_h = roof_h * 0.90
        chimney_x_offset = hw * 0.22 if house['chimney_side'] == 'left' else hw * 0.60
        chimney_x = hx + chimney_x_offset
        chimney_y = hy + hh + (roof_h * 0.35)

        lip_overhang = dp(6)
        lip_w = chimney_w + (lip_overhang * 2)
        lip_h = dp(12)
        lip_x = chimney_x - lip_overhang
        lip_y = chimney_y + chimney_h

        # AABB Collision Box
        i_left, i_right = item['x'], item['x'] + item['size']
        i_bottom, i_top = item['y'], item['y'] + item['size']

        return (i_left < (lip_x + lip_w) and i_right > lip_x and
                i_bottom < (lip_y + lip_h) and i_top > lip_y)

    def draw_game_canvas(self):
        # Clear previous instruction group shapes directly
        self.game_canvas_group.clear()

        # --- 1. ENLARGED HOUSES ---
        for h in self.houses:
            hx, hy = h['x'], h['y']
            hw, hh = self.house_w, self.house_h

            roof_overhang = Scale.min_dim(0.05)
            roof_w = hw + (roof_overhang * 2)
            roof_h = hh * 0.50
            roof_x = hx - roof_overhang
            roof_apex_y = hy + hh + roof_h

            chimney_w = hw * 0.18
            chimney_h = roof_h * 0.90
            chimney_x_offset = hw * 0.22 if h['chimney_side'] == 'left' else hw * 0.60
            chimney_x = hx + chimney_x_offset
            chimney_y = hy + hh + (roof_h * 0.35)

            lip_overhang = dp(6)
            lip_w = chimney_w + (lip_overhang * 2)
            lip_h = dp(12)
            lip_x = chimney_x - lip_overhang
            lip_y = chimney_y + chimney_h

            # Roof & Chimney Color (Nice = Green | Naughty = Red)
            if h['type'] == 'nice':
                self.game_canvas_group.add(Color(0.1, 0.55, 0.2, 1))
            else:
                self.game_canvas_group.add(Color(0.75, 0.1, 0.1, 1))

            self.game_canvas_group.add(Rectangle(pos=(chimney_x, chimney_y), size=(chimney_w, chimney_h)))
            self.game_canvas_group.add(Rectangle(pos=(lip_x, lip_y), size=(lip_w, lip_h)))

            # Wood House Body
            self.game_canvas_group.add(Color(0.45, 0.25, 0.12, 1))
            self.game_canvas_group.add(Rectangle(pos=(hx, hy), size=(hw, hh)))

            # Roof Triangle
            if h['type'] == 'nice':
                self.game_canvas_group.add(Color(0.1, 0.55, 0.2, 1))
            else:
                self.game_canvas_group.add(Color(0.75, 0.1, 0.1, 1))

            roof_vertices = [
                roof_x, hy + hh, 0, 0,
                roof_x + roof_w, hy + hh, 0, 0,
                hx + (hw / 2), roof_apex_y, 0, 0
            ]
            self.game_canvas_group.add(Mesh(vertices=roof_vertices, indices=[0, 1, 2], mode='triangles'))

        # --- 2. DROPPED ITEMS (Presents / Coal) ---
        for item in self.dropped_items:
            self.game_canvas_group.add(Color(1, 1, 1, 1))  # Pure white tint so atlas sprite colors render untinted
            if item['type'] == 'present':
                self.game_canvas_group.add(Rectangle(
                    source='atlas://assets/images/game_sprites/present',
                    pos=(item['x'], item['y']),
                    size=(item['size'], item['size'])
                ))
            else:
                self.game_canvas_group.add(Rectangle(
                    source='atlas://assets/images/game_sprites/coal',
                    pos=(item['x'], item['y']),
                    size=(item['size'], item['size'])
                ))

        # --- 3. SANTA'S SLEIGH ---
        self.game_canvas_group.add(Color(1, 1, 1, 1))
        self.game_canvas_group.add(Rectangle(
            source='atlas://assets/images/game_sprites/santa_sleigh',
            pos=(self.sleigh_x, self.sleigh_y),
            size=(self.sleigh_w, self.sleigh_h)
        ))

        # --- 4. MISSILES ---
        self.game_canvas_group.add(Color(1, 1, 1, 1))
        for m in self.missiles:
            self.game_canvas_group.add(Rectangle(
                source='atlas://assets/images/game_sprites/missile',
                pos=(m['x'], m['y']),
                size=(self.missile_w, self.missile_h)
            ))

    def game_over(self):
        self.game_running = False
        self.stop_engine()

        self.load_high_score()
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()

        self.score_label.text = f"SCORE: {self.score}  |  BEST: {self.high_score}"
        self.play_help_row.opacity = 1
        self.play_help_row.disabled = False
        self.diff_row.opacity = 1
        self.diff_row.disabled = False
        self.start_btn.text = "RETRY FLIGHT"

    def stop_engine(self):
        if self.update_event:
            Clock.unschedule(self.update_event)
            self.update_event = None
        if self.spawn_missile_event:
            Clock.unschedule(self.spawn_missile_event)
            self.spawn_missile_event = None
        if self.spawn_house_event:
            Clock.unschedule(self.spawn_house_event)
            self.spawn_house_event = None

        self.drop_btn_container.opacity = 0
        self.drop_btn_container.disabled = True

        if hasattr(self, 'game_canvas_group'):
            self.game_canvas_group.clear()
        self.missiles = []
        self.houses = []
        self.dropped_items = []

class ProtanopiaEffect(EffectBase):
    glsl = """
    vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords) {
        float r = color.r;
        float g = color.g;
        float b = color.b;
        return vec4(0.56667 * r + 0.43333 * g, 0.55833 * r + 0.44167 * g, 0.24167 * g + 0.75833 * b, color.a);
    }
    """

class DeuteranopiaEffect(EffectBase):
    glsl = """
    vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords) {
        float r = color.r;
        float g = color.g;
        float b = color.b;
        return vec4(0.625 * r + 0.375 * g, 0.70 * r + 0.30 * g, 0.30 * g + 0.70 * b, color.a);
    }
    """

class TritanopiaEffect(EffectBase):
    glsl = """
    vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords) {
        float r = color.r;
        float g = color.g;
        float b = color.b;
        return vec4(0.95 * r + 0.05 * g, 0.433 * g + 0.567 * b, 0.475 * g + 0.525 * b, color.a);
    }
    """

class MonochromeEffect(EffectBase):
    glsl = """
    vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords) {
        float lum = dot(color.rgb, vec3(0.299, 0.587, 0.114));
        return vec4(lum, lum, lum, color.a);
    }
    """

class BrainGamesApp(App):
    
    active_atlas_prefix = StringProperty('atlas://assets/images/game_sprites/')
    
    def update_active_atlas_prefix(self):
        """Updates the active atlas path based on active seasonal state."""
        if self.is_christmas_active():
            self.active_atlas_prefix = 'atlas://assets/images/game_sprites_christmas/'
        elif self.is_halloween_active():
            self.active_atlas_prefix = 'atlas://assets/images/game_sprites_halloween/'
        else:
            self.active_atlas_prefix = 'atlas://assets/images/game_sprites/'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color_blind_mode = 'NONE'
        self.haptics_enabled = True
        self.is_muted = False
        self.current_music_name = 'CLASSIC'
        self.bg_track = None
        self.effect_layer = None
        self.sm = None
        self.seasonal_ui_enabled = True
        self.dev_halloween_override = False

    def build(self):
        Window.bind(on_hardware_back_button=self.on_hardware_back_button)
        
        if platform in ['win', 'linux', 'macosx']:
            Window.size = (360, 640)

        Builder.load_file('main.kv')

        # Load Seasonal Preferences First
        self.seasonal_ui_enabled = web_load_game_data('seasonal_ui_enabled', True)
        self.dev_halloween_override = web_load_game_data('dev_halloween_override', False)
        self.load_seasonal_settings()
        self.load_user_settings()

        # 1. Outer Container for Shader/Colorblind Effects
        self.effect_layer = EffectWidget()

        # 2. Register Screens in ScreenManager
        self.sm = ScreenManager()
        self.sm.add_widget(MainMenuScreen(name='menu'))
        self.sm.add_widget(AboutScreen(name='about'))
        self.sm.add_widget(AchievementsScreen(name='achievements_screen'))
        self.sm.add_widget(SettingsScreen(name='settings'))
        self.sm.add_widget(ToastyMallowScreen(name='toasty_mallow'))
        self.sm.add_widget(FocusFlashScreen(name='focus_flash'))
        self.sm.add_widget(PlanetHopperScreen(name='planet_hopper'))
        self.sm.add_widget(StroopMatchScreen(name='stroop_match'))
        self.sm.add_widget(AirTrafficControlScreen(name='air_traffic'))
        self.sm.add_widget(CodeCaptureScreen(name='code_capture'))
        self.sm.add_widget(PointVelocityScreen(name='point_velocity'))
        self.sm.add_widget(ConsecutiveShapesScreen(name='consecutive_shapes'))
        self.sm.add_widget(MatrixRecallScreen(name='matrix_recall'))
        self.sm.add_widget(RotationalMazeScreen(name='rotational_maze'))
        self.sm.add_widget(SinkyStoneScreen(name='sinky_stone'))
        self.sm.add_widget(GridLockScreen(name='grid_lock'))
        self.sm.add_widget(AgainstGrainScreen(name='against_grain'))
        self.sm.add_widget(HigherEquationScreen(name='higher_equation'))
        self.sm.add_widget(WhatsNextScreen(name='whats_next'))
        self.sm.add_widget(WaiterWaiterScreen(name='waiter_waiter'))
        self.sm.add_widget(GateKeeperScreen(name='gate_keeper'))
        self.sm.add_widget(DropOffScreen(name='drop_off'))
        self.sm.add_widget(ZenBreathingScreen(name='zen_breathing')) 
        self.sm.add_widget(ScreenshotScreen(name='screenshot'))
        self.sm.add_widget(LineFillScreen(name='linefill'))
        self.sm.add_widget(MathInvadersScreen(name='math_invaders'))
        self.sm.add_widget(SequenceSwitchScreen(name='sequence_switch'))
        self.sm.add_widget(TileTurnpikeScreen(name='tile_turnpike'))
        self.sm.add_widget(NeonPythonScreen(name='neon_python'))
        self.sm.add_widget(LockPickScreen(name='lock_pick'))
        self.sm.add_widget(RapidReaderScreen(name='rapid_reader'))
        self.sm.add_widget(CheatsScreen(name='cheats'))
        self.sm.add_widget(HalloweenGameScreen(name='halloween_game'))
        self.sm.add_widget(ChristmasGameScreen(name='christmas_game'))

        # Embed ScreenManager inside EffectWidget
        self.effect_layer.add_widget(self.sm)

        # 3. Load User Preferences & Music
        self.load_user_settings()
        self.load_bg_track(self.current_music_name)
        Clock.schedule_once(lambda dt: self.apply_color_blind_filter(self.color_blind_mode), 0.1)
        
        saved_track = web_load_game_data('current_music_name', 'CLASSIC')
        self.switch_music_track(saved_track)
        
        # FIXED: Return the outer wrapper layout instead of self.sm
        return self.effect_layer
    
    def is_halloween_active(self):
        """Returns True if dev override is ON OR if the current date is in October (Oct 1 - Oct 31)."""
        # 1. Dev Cheat Override Check
        if getattr(self, 'dev_halloween_override', False):
            return True

        # 2. Seasonal Date Check (October 1 to October 31)
        if getattr(self, 'seasonal_ui_enabled', True):
            now = datetime.now()
            if now.month == 10:  # October
                return True

        return False
    
    def is_halloween_active(self):
        """Returns True if Halloween UI should be displayed."""
        if not self.seasonal_ui_enabled:
            return False
        if self.dev_halloween_override:
            return True
            
        # Real-time seasonal check fallback
        from datetime import datetime
        today = datetime.now()
        return today.month == 10  # Active for the month of October

    def get_primary_bg_color(self):
        """Returns Spooky Purple if Halloween is active, else Deep Cosmic Blue."""
        if self.is_halloween_active():
            return (0.12, 0.04, 0.22, 1)  # Dark Spooky Purple (#1F0A38)
        return (0.04, 0.06, 0.17, 1)      # Classic Dark Blue (#0A0F2C)
    
    def get_accent_color(self):
        """Returns Glowing Orange if Halloween is active, else Neon Cyan Blue."""
        if self.is_halloween_active():
            return (1.0, 0.5, 0.0, 1)     # Pumpkin / Glowing Orange (#FF8000)
        return (0.0, 0.75, 1.0, 1)        # Classic Arcade Cyan (#00BFFF)

    def is_christmas_active(self):
        """Checks if Christmas seasonal UI should be rendered."""
        if not getattr(self, 'seasonal_ui_enabled', True):
            return False
        if getattr(self, 'dev_christmas_override', False):
            return True
        # Date check fallback
        today = datetime.now()
        return today.month == 12 or (today.month == 1 and today.day <= 6)
    
    '''def is_christmas_active(self):
        "Active during December if seasonal UI is enabled, or if dev Christmas override is True."
        if self.dev_christmas_override:
            return True
        if not self.seasonal_ui_enabled:
            return False
        return datetime.now().month == 12'''
    
    def save_seasonal_settings(self):
        """Saves seasonal UI preference and dev overrides into persistent JSON save file."""
        web_save_game_data('seasonal_ui_enabled', self.seasonal_ui_enabled)
        web_save_game_data('dev_halloween_override', self.dev_halloween_override)
        web_save_game_data('dev_christmas_override', self.dev_christmas_override)
        
    def load_seasonal_settings(self):
        """Loads persistent seasonal state and dev overrides from JSON."""
        self.seasonal_ui_enabled = web_load_game_data('seasonal_ui_enabled', True)
        self.dev_halloween_override = web_load_game_data('dev_halloween_override', False)
        self.dev_christmas_override = web_load_game_data('dev_christmas_override', False)
        
    def refresh_all_screen_backgrounds(self):
        if hasattr(self, 'sm') and self.sm:
            for screen in self.sm.screens:
                apply_theme_background(screen)

    def load_user_settings(self):
        """Loads all persistent user preferences from disk."""
        self.color_blind_mode = web_load_game_data('color_blind_mode', 'NONE')
        self.haptics_enabled = web_load_game_data('haptics_enabled', True)
        self.current_music_name = web_load_game_data('music_track', 'CLASSIC')
        self.is_muted = web_load_game_data('is_muted', False)
        
        saved_vol = web_load_game_data('volume', 0.5)
        if self.bg_track:
            self.bg_track.volume = 0.0 if self.is_muted else saved_vol

    def save_color_blind_setting(self, mode):
        self.color_blind_mode = mode
        web_save_game_data('color_blind_mode', mode)

    def save_haptics_setting(self, enabled):
        self.haptics_enabled = enabled
        web_save_game_data('haptics_enabled', enabled)

    def save_music_setting(self, track_name):
        self.current_music_name = track_name
        web_save_game_data('music_track', track_name)

    def save_audio_settings(self):
        if self.bg_track:
            web_save_game_data('volume', self.bg_track.volume)
            web_save_game_data('is_muted', self.is_muted)

    def apply_color_blind_filter(self, mode):
        """Swaps the active EffectBase class applied to the EffectWidget."""
        mode_map = {
            'PROTANOPIA': [ProtanopiaEffect()],
            'DEUTERANOPIA': [DeuteranopiaEffect()],
            'TRITANOPIA': [TritanopiaEffect()],
            'MONOCHROME': [MonochromeEffect()],
            'NONE': []
        }
        
        if hasattr(self, 'effect_layer') and self.effect_layer:
            self.effect_layer.effects = mode_map.get(mode, [])

    def transform_color(self, rgba):
        """Helper method to transform an (r, g, b, a) tuple based on active mode."""
        r, g, b = rgba[0], rgba[1], rgba[2]
        a = rgba[3] if len(rgba) > 3 else 1.0
        mode = getattr(self, 'color_blind_mode', 'NONE')

        if mode == 'PROTANOPIA':
            nr = 0.56667 * r + 0.43333 * g
            ng = 0.55833 * r + 0.44167 * g
            nb = 0.24167 * g + 0.75833 * b
            return (nr, ng, nb, a)
        elif mode == 'DEUTERANOPIA':
            nr = 0.625 * r + 0.375 * g
            ng = 0.70 * r + 0.30 * g
            nb = 0.30 * g + 0.70 * b
            return (nr, ng, nb, a)
        elif mode == 'TRITANOPIA':
            nr = 0.95 * r + 0.05 * g
            ng = 0.433 * g + 0.567 * b
            nb = 0.475 * g + 0.525 * b
            return (nr, ng, nb, a)
        elif mode == 'MONOCHROME':
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            return (lum, lum, lum, a)
            
        return (r, g, b, a)

    def on_hardware_back_button(self, window, key, *args):
        if key == 27:  # Android back key / ESC
            if self.sm and self.sm.current != 'menu':
                self.sm.current = 'menu'
                return True
        return False
    
    def on_pause(self):
        if self.bg_track and self.bg_track.state == 'play':
            self.bg_track.pause()
        return True

    def on_resume(self):
        if self.bg_track and hasattr(self.bg_track, 'resume'):
            self.bg_track.resume()

    def get_track_file(self, track_name):
        mapping = {
            'CLASSIC': 'assets/audios/arcade_theme.ogg',
            'HARDCORE': 'assets/audios/arcade_theme_hardcore.ogg',
            'CHILL': 'assets/audios/arcade_theme_chill.ogg',
            'HALLOWEEN': 'assets/audios/arcade_theme_halloween.ogg'
        }
        return mapping.get(track_name, 'assets/audios/arcade_theme.ogg')

    def load_bg_track(self, track_name):
        current_vol = self.bg_track.volume if self.bg_track else 0.5
        if self.bg_track:
            self.bg_track.stop()
            
        file_path = self.get_track_file(track_name)
        self.bg_track = SoundLoader.load(file_path)
        if self.bg_track:
            self.bg_track.loop = True
            self.bg_track.volume = 0.0 if self.is_muted else current_vol
            self.bg_track.play()

    def switch_music_track(self, track_name):
        """Switches background audio stream and saves choice."""
        music_files = {
            'CLASSIC': 'assets/audios/arcade_theme.ogg',
            'HARDCORE': 'assets/audios/arcade_theme_hardcore.ogg',
            'CHILL': 'assets/audios/arcade_theme_chill.ogg',
            'HALLOWEEN': 'assets/audios/arcade_theme_halloween.ogg',
            'CHRISTMAS': 'assets/audios/arcade_theme_christmas.ogg'
        }

        if track_name not in music_files:
            track_name = 'CLASSIC'

        self.current_music_name = track_name
        current_vol = self.bg_track.volume if hasattr(self, 'bg_track') and self.bg_track else 0.5

        if hasattr(self, 'bg_track') and self.bg_track:
            self.bg_track.stop()
            self.bg_track = None

        file_path = music_files[track_name]
        if os.path.exists(file_path):
            self.bg_track = SoundLoader.load(file_path)
            if self.bg_track:
                self.bg_track.loop = True
                self.bg_track.volume = 0.0 if getattr(self, 'is_muted', False) else current_vol
                self.bg_track.play()

        # Save track name to JSON
        web_save_game_data('current_music_name', self.current_music_name)
        
    def on_start(self):
        # Sync atlas path on launch
        self.update_active_atlas_prefix()

if __name__ == "__main__":
    BrainGamesApp().run()