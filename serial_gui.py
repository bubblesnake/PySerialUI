#!/usr/bin/env python3
'''
Serial Interface GUI Application
A simple GUI for interfacing with serial ports.
'''

import tkinter as tk
from tkinter import ttk, scrolledtext
import serial
import serial.tools.list_ports
import threading
import time


class SerialGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Interface GUI")
        self.root.geometry("600x500")
        self.root.minsize(500, 400)

        self.serial_port = None
        self.is_reading = False
        self.read_thread = None

        self.create_widgets()
        self.refresh_ports()

    def create_widgets(self):
        # Create frame for controls
        control_frame = ttk.LabelFrame(self.root, text="Connection Settings")
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # Serial port selection
        ttk.Label(control_frame, text="Serial Port:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.port_combo = ttk.Combobox(control_frame, width=30)
        self.port_combo.grid(row=0, column=1, padx=5, pady=5)

        refresh_btn = ttk.Button(control_frame, text="Refresh", command=self.refresh_ports)
        refresh_btn.grid(row=0, column=2, padx=5, pady=5)

        # Baud rate selection
        ttk.Label(control_frame, text="Baud Rate:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.baud_combo = ttk.Combobox(control_frame, values=["9600", "115200", "460800"], width=15)
        self.baud_combo.current(1)  # Default to 115200
        self.baud_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # Connection buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=2, column=0, columnspan=3, pady=5)

        self.connect_btn = ttk.Button(btn_frame, text="Connect", command=self.open_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=5)

        self.disconnect_btn = ttk.Button(btn_frame, text="Disconnect", command=self.close_connection, state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT, padx=5)

        # Text display area
        display_frame = ttk.LabelFrame(self.root, text="Serial Output")
        display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create a scrolled text widget for output display
        self.output_text = scrolledtext.ScrolledText(display_frame, wrap=tk.WORD, width=60, height=15)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.output_text.config(state=tk.DISABLED)

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Not connected")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def refresh_ports(self):
        """Refresh the list of available serial ports"""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.current(0)
        else:
            self.status_var.set("No serial ports found")

    def open_connection(self):
        """Open the selected serial connection"""
        port = self.port_combo.get()
        if not port:
            self.status_var.set("Error: No port selected")
            return

        try:
            baud_rate = int(self.baud_combo.get())
            self.serial_port = serial.Serial(port, baud_rate, timeout=1)
            self.status_var.set(f"Connected to {port} at {baud_rate} baud")
            
            # Update button states
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            
            # Start reading from the port
            self.is_reading = True
            self.read_thread = threading.Thread(target=self.read_serial, daemon=True)
            self.read_thread.start()
            
        except ValueError:
            self.status_var.set("Error: Invalid baud rate")
        except serial.SerialException:
            self.status_var.set(f"Error: Could not open port {port}")

    def close_connection(self):
        """Close the serial connection"""
        if self.serial_port and self.serial_port.is_open:
            self.is_reading = False
            if self.read_thread:
                self.read_thread.join(timeout=1.0)
            
            self.serial_port.close()
            self.serial_port = None
            
            # Update button states
            self.connect_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            
            self.status_var.set("Disconnected")

    def read_serial(self):
        """Read data from the serial port in a separate thread"""
        while self.is_reading and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    if data:
                        self.display_data(data)
            except serial.SerialException:
                self.root.after(0, self.handle_disconnect)
                break
            time.sleep(0.1)

    def display_data(self, data):
        """Display received data in the text widget"""
        try:
            # Try to decode as UTF-8 first
            text = data.decode('utf-8', errors='replace')
            
            # Use after method to safely update the UI from a non-main thread
            self.root.after(0, self._update_display, text)
        except Exception as e:
            self.root.after(0, self._update_display, f"[Error displaying data: {e}]")

    def _update_display(self, text):
        """Update the display text (called from the main thread)"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, text)
        # Auto-scroll to end
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)

    def handle_disconnect(self):
        """Handle unexpected disconnection"""
        self.status_var.set("Error: Serial port disconnected unexpectedly")
        self.close_connection()


if __name__ == "__main__":
    root = tk.Tk()
    app = SerialGUI(root)
    root.mainloop()