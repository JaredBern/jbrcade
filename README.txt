
Electric Blue	#00BFFF	Bright cyan glow for buttons and tile outlines.
Deep Space Navy	#0A0F2C	Background base — dark enough to make neon pop.
Magenta Pulse	#FF00A0	Accent for highlights, score text, and transitions.
Laser Purple	#7D3CFF	Secondary glow for icons and borders.
Sunset Orange	#FF6B00	Warm contrast for active states and notifications.
Pixel Gold	#FFD700	Trophy icons, highscore highlights.
Grid Cyan	#00FFFF	Subtle grid lines or menu separators.

#building the app after spec file changes
cd "C:\Users\jared\Desktop\mini_games_app\docker"

docker-compose up -d

docker compose exec buildozer buildozer android clean

docker compose exec buildozer buildozer -v android debug

#building the app for daily testing
docker compose exec buildozer buildozer -v android debug

#using atlas file for images
Rectangle:
    source: 'atlas://assets/images/game_sprites/tile_preview'
    pos: self.pos
    size: self.size

#converting piskel coordinates to atlas coordinates
H = height of sprite sheet
Xp,Yp = piskel coords
Xa,Ya = atlas coords

Xa = Xp - 1
Ya = H - Yp

It is completely natural to feel like hitting a disk space wall means you need to abandon ship and install a dedicated Linux OS. However, you do **not** need to switch your computer over to Linux to handle this project as it grows to hundreds of megabytes.

The storage constraint you just experienced actually has nothing to do with your game code or asset sizes. It is a one-time bottleneck caused by how WSL2 (Windows Subsystem for Linux) handles its virtual hard drive limits by default on Windows.

---

### What Actually Caused the "Out of Space" Crash?

Your game app code and image assets take up almost no room. The crash happened because **compiling Python from source** for a mobile architecture requires compiling thousands of C-language files (`.o` object files).

When Buildozer compiles Python, it unpacks a massive temporary workspace inside the container. This temporary build footprint can easily balloon to **4GB to 8GB** of intermediate scratch files. Once the final APK is built, all those temporary files are useless, but they remain sitting inside the virtual drive cache. Because WSL2 expands its virtual disk file (`ext4.vhdx`) to accommodate that temporary spike but *never automatically shrinks it back down*, you hit the maximum default storage cap that Windows allocates to WSL2.

---

### Why Scaling Up Your App in the Future Won't Break It

As your game app grows from 10MB to 500MB with more assets, music tracks, and code files, your disk usage won't scale up aggressively like this again.

1. **The Python Core is Already Built:** Buildozer only builds the core Android-compatible Python interpreter and Kivy binaries *once*. For future builds, it checks its cache, skips the heavy C-compilation phase entirely, and only packages your updated game assets.
2. **Assets are Light to Package:** Adding music, artwork, or scripts doesn't require compiling complex C-libraries. If you add a 5MB music file, it adds exactly 5MB to the build process—not gigabytes of intermediate compiler files.

---

### How to Prevent This Going Forward (Without Swapping OS)

If you find yourself running low on space again down the line, you can fix it permanently directly inside Windows using two configuration adjustments:

#### 1. Give WSL2 a Higher Storage Ceiling

By default, Windows caps the WSL2 virtual drive at a specific size (often 256GB, but it can be restricted on certain Windows profiles). You can explicitly tell Windows to allow the virtual drive to expand up to a larger limit (like 500GB) by editing your global configuration file.

* Open Notepad and open `%USERPROFILE%\.wslconfig`
* Add these lines to give the Linux backend access to more virtual drive room and system memory:
```text
[wsl2]
memory=8GB
sparseVhd=true

```



> *Note: Setting `sparseVhd=true` tells Windows to automatically shrink the `ext4.vhdx` file when files inside Docker are deleted, completely eliminating the need to use the `diskpart compact` tool manually!*

#### 2. Periodically Clean Your Docker System

Keep a habit of running a clean command between major project changes to drop stale data layers:

```powershell
docker system prune -f

```

You are perfectly fine staying on Windows! The environment you have set up via Docker and WSL2 gives you the exact same build stability as a native Linux machine without the hassle of reformatting your main workstation computer. Let's see if your compilation pass finishes smoothly now that the workspace is clear.

To keep your codebase clean and prevent you from having to copy-paste huge chunks of layout logic into all 17 games, the most professional way to implement this is to build a reusable **InstructionOverlay** class right inside `main.py`.

This overlay can be added dynamically to any screen's layout. It sits perfectly inside the existing layout hierarchy, meaning you don't have to navigate to a new screen or break your game state management.

---

### 1. The Reusable Component Code

Paste this snippet near the top of your `main.py` file (right below your imports and above your screen classes):

```python
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

```

---

### 2. How to Wire It Into Each Sub-Game Screen

To apply this to any screen, you only need to perform three quick adaptations inside the target screen class. Let's look at a step-by-step example using `ToastyMallowScreen`:

#### Step A: Replace the `Play` Button with a Split Box Layout

Locate where `self.start_btn` is instantiated inside the screen's `__init__` constructor method and change it to share space with the new help button:

```python
        # --- FIND THIS BLOCK IN __init__ ---
        # self.start_btn = Button(text="PLAY", ...)
        # self.menu_buttons.add_widget(self.start_btn)

        # --- REPLACE IT WITH THIS ---
        play_help_row = BoxLayout(orientation='horizontal', spacing=dp(10))
        self.menu_buttons.add_widget(play_help_row)

        self.start_btn = Button(
            text="PLAY", font_size='20sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.75, 1, 1), color=(0.04, 0.06, 0.17, 1),
            size_hint_x=0.8
        )
        self.start_btn.bind(on_release=self.start_game_countdown)
        play_help_row.add_widget(self.start_btn)

        # Compact Help Callout Button Slot
        self.help_btn = Button(
            text="?", font_size='18sp', font_name='assets/fonts/ARCADE_N.TTF',
            background_normal='', background_color=(0, 0.5, 0.8, 1), color=(1, 1, 1, 1),
            size_hint_x=0.2
        )
        self.help_btn.bind(on_release=self.show_instructions_overlay)
        play_help_row.add_widget(self.help_btn)

```

#### Step B: Add Interface Controller Actions to the Screen Class

Add these two short wrapper methods anywhere inside your screen class definitions to safely orchestrate loading states:

```python
    def show_instructions_overlay(self, instance):
        # Disable underneath UI inputs while help is present
        self.menu_buttons.disabled = True
        self.back_btn.disabled = True
        
        # Placeholders to customize per sub-game
        game_name = "Toasty Mallow"
        placeholders = [
            "PLACEHOLDER BULLET POINT RULE NUMBER 1",
            "PLACEHOLDER BULLET POINT RULE NUMBER 2",
            "PLACEHOLDER BULLET POINT RULE NUMBER 3"
        ]
        
        overlay = InstructionOverlay(
            game_name=game_name, 
            rules_list=placeholders, 
            close_callback=self.on_instructions_closed
        )
        self.layout.add_widget(overlay)

    def on_instructions_closed(self):
        # Restore access controls cleanly when "READY!" fires
        self.menu_buttons.disabled = False
        self.back_btn.disabled = False

```

#### Step C: Secure Menu Transitions

To make sure the layout switches back flawlessly when a player switches screens, hide the overlay if it's open. Add this step inside `go_back_to_menu`:

```python
    def go_back_to_menu(self, instance=None):
        self.cleanup_engine()
        # 🟢 NEW: Clean away instruction widgets if they back out mid-view
        for child in list(self.layout.children):
            if isinstance(child, InstructionOverlay):
                self.layout.remove_widget(child)
        self.manager.current = 'menu'

```

Repeat Steps A, B, and C for any sub-game screen you want to support. All you need to edit per screen is the `game_name` string and the `placeholders` string list!