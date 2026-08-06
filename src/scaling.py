# utils/scaling.py
from kivy.core.window import Window

# Reference baseline resolution (Standard modern phone height in pixels)
BASE_HEIGHT = 800.0
BASE_WIDTH = 450.0

class Scale:
    @staticmethod
    def height_pct(percentage: float) -> float:
        """Returns pixel value based on percentage of current screen height (0.0 to 1.0)."""
        return Window.height * percentage

    @staticmethod
    def width_pct(percentage: float) -> float:
        """Returns pixel value based on percentage of current screen width (0.0 to 1.0)."""
        return Window.width * percentage

    @staticmethod
    def font(size_px: float) -> float:
        """
        Scales a base pixel font size proportionally to current screen height.
        Designed so font sizes look identical relative to the screen on phones and tablets.
        """
        return (Window.height / BASE_HEIGHT) * size_px

    @staticmethod
    def vel_h(base_velocity: float) -> float:
        """
        Scales vertical velocity or gravity relative to current screen height.
        Pass in the velocity tuned for a standard ~800px tall screen.
        """
        return (Window.height / BASE_HEIGHT) * base_velocity

    @staticmethod
    def vel_w(base_velocity: float) -> float:
        """
        Scales horizontal velocity or speed relative to current screen width.
        Pass in the speed tuned for a standard ~450px wide screen.
        """
        return (Window.width / BASE_WIDTH) * base_velocity

    @staticmethod
    def min_dim(percentage: float) -> float:
        """
        Useful for square objects/sprites (like coins or aircraft icons).
        Scales based on the smaller screen dimension so sprites don't get overly huge on wide tablets.
        """
        return min(Window.width, Window.height) * percentage
    
scale_font = Scale.font
scale_hpct = Scale.height_pct
scale_wpct = Scale.width_pct