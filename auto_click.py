import sys
import time
import ctypes
import threading
import tkinter as tk
from tkinter import ttk

# Windows API Constants for Simulating Clicks
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

# Virtual Key Code for F6
VK_F6 = 0x75

# Global States
clicking = False
running = True
button_type = "left"
click_interval = 0.1  # in seconds


def simulate_click():
    """Simulates a mouse press and release at the current cursor position."""
    if button_type == "left":
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.005)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    else:
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        time.sleep(0.005)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)


def is_f6_pressed():
    """Checks if the F6 key is currently pressed down globally on Windows."""
    # GetAsyncKeyState checks the global state of the key
    return (ctypes.windll.user32.GetAsyncKeyState(VK_F6) & 0x8000) != 0


def clicker_worker():
    """Background thread that handles the clicking intervals."""
    global clicking
    while running:
        if clicking:
            simulate_click()
            time.sleep(click_interval)
        else:
            time.sleep(0.01)  # Reduce CPU usage when idle


def hotkey_monitor(status_callback):
    """Background thread that monitors the F6 key to toggle the clicking state."""
    global clicking
    key_was_down = False
    while running:
        key_is_down = is_f6_pressed()
        if key_is_down and not key_was_down:
            # F6 was just pressed (transitioned from up to down)
            clicking = not clicking
            status_callback()
        key_was_down = key_is_down
        time.sleep(0.05)  # Debounce delay


class AutoclickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AutoClicker Pro")
        self.root.geometry("380x320")
        self.root.resizable(False, False)

        # Style configurations
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Dark theme palette
        self.bg_color = "#1E1E2E"
        self.fg_color = "#CDD6F4"
        self.accent_color = "#89B4FA"
        self.card_color = "#313244"
        self.green_color = "#A6E3A1"
        self.red_color = "#F38BA8"

        self.root.configure(bg=self.bg_color)

        # Main wrapper frame
        main_frame = tk.Frame(root, bg=self.bg_color, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header Title
        title_label = tk.Label(
            main_frame,
            text="AUTOCLICKER",
            font=("Consolas", 18, "bold"),
            bg=self.bg_color,
            fg=self.accent_color
        )
        title_label.pack(pady=(0, 15))

        # Settings Card Frame
        settings_frame = tk.Frame(main_frame, bg=self.card_color, bd=0, relief=tk.FLAT, padx=15, pady=15)
        settings_frame.pack(fill=tk.X, pady=5)

        # Click Interval Setting
        interval_label = tk.Label(
            settings_frame,
            text="Click Interval (ms):",
            font=("Segoe UI", 10),
            bg=self.card_color,
            fg=self.fg_color
        )
        interval_label.grid(row=0, column=0, sticky=tk.W, pady=8)

        self.interval_entry = tk.Entry(
            settings_frame,
            font=("Segoe UI", 10),
            bg=self.bg_color,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            bd=1,
            relief=tk.SOLID,
            width=10,
            justify=tk.CENTER
        )
        self.interval_entry.insert(0, "100")
        self.interval_entry.grid(row=0, column=1, padx=(10, 0), pady=8)
        self.interval_entry.bind("<KeyRelease>", self.update_interval)

        # Mouse Button Selection
        button_label = tk.Label(
            settings_frame,
            text="Mouse Button:",
            font=("Segoe UI", 10),
            bg=self.card_color,
            fg=self.fg_color
        )
        button_label.grid(row=1, column=0, sticky=tk.W, pady=8)

        self.button_var = tk.StringVar(value="left")
        
        self.rb_left = tk.Radiobutton(
            settings_frame,
            text="Left Click",
            variable=self.button_var,
            value="left",
            command=self.update_button,
            bg=self.card_color,
            fg=self.fg_color,
            selectcolor=self.card_color,
            activebackground=self.card_color,
            activeforeground=self.accent_color,
            font=("Segoe UI", 9)
        )
        self.rb_left.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=8)

        self.rb_right = tk.Radiobutton(
            settings_frame,
            text="Right Click",
            variable=self.button_var,
            value="right",
            command=self.update_button,
            bg=self.card_color,
            fg=self.fg_color,
            selectcolor=self.card_color,
            activebackground=self.card_color,
            activeforeground=self.accent_color,
            font=("Segoe UI", 9)
        )
        self.rb_right.grid(row=1, column=1, sticky=tk.E, pady=8)

        # Global Hotkey Instruction
        hotkey_frame = tk.Frame(main_frame, bg=self.bg_color)
        hotkey_frame.pack(fill=tk.X, pady=10)

        hotkey_text = tk.Label(
            hotkey_frame,
            text="Hotkey: [ F6 ] (Press globally to Start / Stop)",
            font=("Segoe UI", 10, "italic"),
            bg=self.bg_color,
            fg=self.fg_color
        )
        hotkey_text.pack(anchor=tk.CENTER)

        # Status Display Frame
        self.status_label = tk.Label(
            main_frame,
            text="STATUS: STOPPED",
            font=("Segoe UI", 12, "bold"),
            bg=self.red_color,
            fg=self.bg_color,
            padx=20,
            pady=8,
            bd=0,
            relief=tk.FLAT
        )
        self.status_label.pack(fill=tk.X, pady=(10, 0))

    def update_interval(self, event=None):
        """Validates and updates the clicking interval dynamically from GUI entry."""
        global click_interval
        try:
            val = float(self.interval_entry.get())
            if val < 1:
                val = 1
            click_interval = val / 1000.0
        except ValueError:
            pass  # Keep previous valid value on invalid key inputs

    def update_button(self):
        """Updates the button to click (left/right) dynamically from GUI radiobuttons."""
        global button_type
        button_type = self.button_var.get()

    def refresh_status(self):
        """Refreshes the GUI status display label when state toggles."""
        if clicking:
            self.status_label.config(text="STATUS: CLICKING (ACTIVE)", bg=self.green_color)
        else:
            self.status_label.config(text="STATUS: STOPPED", bg=self.red_color)


def on_closing():
    """Handles clean termination of background threads on application close."""
    global running, clicking
    clicking = False
    running = False
    root.destroy()
    sys.exit(0)


if __name__ == "__main__":
    # Initialize TKinter GUI Window
    root = tk.Tk()
    app = AutoclickerApp(root)
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Start Background click and hotkey monitoring threads
    t_click = threading.Thread(target=clicker_worker, daemon=True)
    t_hotkey = threading.Thread(target=hotkey_monitor, args=(app.refresh_status,), daemon=True)

    t_click.start()
    t_hotkey.start()

    root.mainloop()
