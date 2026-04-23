"""Desktop emulator for the Waveshare 7.5" e-ink panel."""

from __future__ import annotations
import logging
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk

logger = logging.getLogger(__name__)

WIDTH = 800
HEIGHT = 480

class MockEPD7in5V2:
    """Desktop emulator that mimics the `waveshare_epd.epd7in5_V2.EPD` API."""

    width = WIDTH
    height = HEIGHT

    def __init__(self):
        """Initialize the emulator state."""
        self._root: tk.Tk | None = None
        self._canvas: tk.Canvas | None = None
        self._toolbar = None
        self._status_var: tk.StringVar | None = None
        self._tk_image = None
        self._canvas_image_id = None
        self._current = Image.new("1", (WIDTH, HEIGHT), 255)

    def _safe_update(self):
        """Safely update the emulator state."""
        if not self._root:
            return
        try:
            self._root.update_idletasks()
            self._root.update()
        except tk.TclError:
            logger.debug("[emulator] window closed")
            self._root = None
            self._canvas = None
            self._status_var = None
            self._canvas_image_id = None

    def _ensure_window(self):
        """Ensure the window is visible."""
        if self._root is None or not self._root.winfo_exists():
            self._root = tk.Tk()
            self._root.title("PiDash Emulator")
            self._root.resizable(False, False)

            container = ttk.Frame(self._root, padding=8)
            container.pack(fill="both", expand=True)

            display_shell = ttk.Frame(container, padding=6, relief="solid", borderwidth=1)
            display_shell.pack(side="top")

            self._canvas = tk.Canvas(
                display_shell,
                width=WIDTH,
                height=HEIGHT,
                highlightthickness=0,
                bg="#e8e8e8",
            )
            self._canvas.pack()

            self._toolbar = ttk.Frame(container, padding=(0, 6, 0, 0))
            self._toolbar.pack(side="bottom", fill="x")

            ttk.Button(self._toolbar, text="Clear", command=self._toolbar_clear).pack(
                side="left", padx=(0, 6)
            )
            ttk.Button(self._toolbar, text="Save PNG", command=self._toolbar_save).pack(
                side="left", padx=(0, 10)
            )

            ttk.Separator(self._toolbar, orient="vertical").pack(side="left", fill="y", padx=(0, 8))

            status_var = tk.StringVar(value="Ready")
            self._status_var = status_var
            ttk.Label(self._toolbar, textvariable=status_var, anchor="e").pack(
                side="right", fill="x", expand=True
            )

    def _set_status(self, msg: str):
        """Set the status of the emulator."""
        if self._status_var is not None:
            self._status_var.set(msg)
        self._safe_update()

    def _toolbar_clear(self):
        """Clear the toolbar."""
        self.clear()
        self._set_status("Cleared")

    def _toolbar_save(self):
        """Save an image screenshot of the emulated display."""
        path = filedialog.asksaveasfilename(
            title="Save emulator snapshot",
            defaultextension=".png",
            filetypes=[("PNG image", "*.png")],
            initialfile="emulator_snapshot.png",
        )
        if not path:
            self._set_status("Save canceled")
            return
        self._current.save(path)
        self._set_status(f"Saved: {path}")
        logger.debug("[emulator] saved snapshot to %s", path)

    def _render(self, image: Image.Image):
        """Render the emulator."""
        self._ensure_window()
        if self._canvas is None:
            return
        rgb = image.convert("RGB")
        self._tk_image = ImageTk.PhotoImage(rgb)
        if self._canvas_image_id is None:
            self._canvas_image_id = self._canvas.create_image(
                0,
                0,
                anchor=tk.NW,
                image=self._tk_image
            )
        else:
            self._canvas.itemconfig(self._canvas_image_id, image=self._tk_image)
        self._safe_update()

    def init(self):
        """Initialize the emulator."""
        logger.debug("[emulator] init")
        self._ensure_window()
        return 0

    def init_fast(self):
        """Initialize the emulator. (Mock fast_init)."""
        logger.debug("[emulator] init_fast")
        return self.init()

    def clear(self):
        """Clear the emulator."""
        logger.debug("[emulator] clear")
        self._current = Image.new("1", (WIDTH, HEIGHT), 255)
        self._render(self._current)

    def getbuffer(self, image: Image.Image):
        """Return the emulator's buffer."""
        return image

    def display(self, image):
        """Display the emulator's buffer."""
        logger.debug("[emulator] display")
        img = image if isinstance(image, Image.Image) else self._current
        self._current = img
        self._render(img)
        self._set_status("Updated")

    # pylint: disable=invalid-name
    # disabled because this is the name that the waveshare library uses
    def display_Partial(self, image, *_args):
        """Display the emulator's buffer."""
        logger.debug("[emulator] display_partial")
        self.display(image)

    def sleep(self):
        """Sleep the emulator."""
        logger.debug("[emulator] sleep")
        self._set_status("Sleeping")

    def update(self):
        """Update the emulator's buffer."""
        self._safe_update()

    def mainloop(self):
        """Main loop of the emulator."""
        if self._root and self._root.winfo_exists():
            self._root.mainloop()

    # pylint: disable=invalid-name,too-few-public-methods
    # disabled because this is the name that the waveshare library uses
    # And we only need to mock one method
    class epdconfig:
        """Mock emulator config."""
        @staticmethod
        def module_exit(cleanup: bool = False):
            """Exit the emulator."""
            logger.debug("[emulator] module_exit cleanup=%s", cleanup)
