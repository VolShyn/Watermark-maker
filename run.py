#!/usr/bin/env python3
"""
Launcher
"""
import os
import sys

# add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)


from gui import tk, ImageProcessorApp

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessorApp(root)
    root.mainloop()
