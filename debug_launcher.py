#!/usr/bin/env python3
"""
Debug launcher for serial_gui.py
Sets a breakpoint at the process_text method
"""

import pdb
import tkinter as tk
import importlib
import serial_gui
import types

# Patch the process_text method to include a breakpoint
original_process_text = serial_gui.AnsiColorizer.process_text

def patched_process_text(self, text):
    # This is where the debugger will stop
    breakpoint()  # Python 3.7+ breakpoint() function
    return original_process_text(self, text)

# Apply the monkey patch
serial_gui.AnsiColorizer.process_text = patched_process_text

# Start the application
if __name__ == "__main__":
    print("Starting serial_gui in debug mode with breakpoint at process_text()")
    print("When text with ANSI codes is received, the debugger will pause execution")
    print("Use 'n' to step to next line, 'c' to continue, 'q' to quit debugger")
    root = tk.Tk()
    app = serial_gui.SerialGUI(root)
    root.mainloop()