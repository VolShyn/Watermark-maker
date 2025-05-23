#!/usr/bin/env python3
"""
Launcher
"""
import os
import sys
from gui import tk, ImageProcessorApp

WATERMARK_TEXT = '3D_Print'
WATERMARK_OPACITY = 0.3       # 0.0 transparent, 1.0 opaque
WATERMARK_THICKNESS = 2
BORDER_COLOR = (228, 100, 0)    # blue border (BGR)
BORDER_THICKNESS = 10


# add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessorApp(root)
    root.mainloop()
