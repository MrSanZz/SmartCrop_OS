#!/usr/bin/env python3
import sys
import os

def check_dependencies():
    missing = []
    try:
        import PyQt6
    except ImportError:
        try:
            import PyQt5
        except ImportError:
            missing.append("PyQt6 or PyQt5")

    try:
        import cv2
    except ImportError:
        missing.append("opencv-python")

    try:
        import numpy
    except ImportError:
        missing.append("numpy")

    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")

    if missing:
        print("=" * 55)
        print("  SmartCrop Pro — Missing Dependencies")
        print("=" * 55)
        print("\nPlease install the required packages:\n")
        print("  pip install PyQt6 opencv-python numpy Pillow rembg\n")
        print("Missing:")
        for m in missing:
            print(f"  - {m}")
        print("\nFor background removal (Mode 2), also install:")
        print("  pip install rembg onnxruntime")
        print("=" * 55)
        sys.exit(1)

check_dependencies()

from app import SmartCropApp

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    PYQT_VERSION = 6
except ImportError:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    PYQT_VERSION = 5

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("SmartCrop Pro")
    app.setApplicationVersion("1.0.0")

    if PYQT_VERSION == 6:
        app.setStyle("Fusion")

    window = SmartCropApp()
    window.show()
    sys.exit(app.exec())