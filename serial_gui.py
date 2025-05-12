#!/usr/bin/env python3
'''
Serial Interface GUI Application
A simple GUI for interfacing with serial ports.
'''

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import serial
import serial.tools.list_ports
import threading
import time
import re
import datetime
import binascii
import sys
import logging


# Configure logging system
class LogLevel:
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    NONE = 100  # Special level to disable logging


class Logger:
    """Simple logging utility with different log levels"""

    def __init__(self, level=LogLevel.INFO):
        self.level = level
        self._init_logger()

    def _init_logger(self):
        """Initialize the Python logger"""
        self.logger = logging.getLogger("PySerialUI")
        self.logger.setLevel(logging.DEBUG)

        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)

        # Create formatter
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)

        # Add handler to logger
        self.logger.addHandler(handler)

        # Prevent propagation to root logger
        self.logger.propagate = False

    def set_level(self, level):
        """Set the logging level"""
        self.level = level

    def debug(self, message):
        """Log debug message"""
        if self.level <= LogLevel.DEBUG:
            self.logger.debug(message)

    def info(self, message):
        """Log info message"""
        if self.level <= LogLevel.INFO:
            self.logger.info(message)

    def warning(self, message):
        """Log warning message"""
        if self.level <= LogLevel.WARNING:
            self.logger.warning(message)

    def error(self, message):
        """Log error message"""
        if self.level <= LogLevel.ERROR:
            self.logger.error(message)

    def critical(self, message):
        """Log critical message"""
        if self.level <= LogLevel.CRITICAL:
            self.logger.critical(message)


# Create a global logger instance
logger = Logger(LogLevel.ERROR)


class AnsiColorizer:
    """Parser for ANSI escape codes to apply formatting to tkinter Text widget"""

    # ANSI escape sequence regex pattern
    ANSI_PATTERN = re.compile(r'\x1b\[((?:\d+;)*\d+)?([a-zA-Z])')

    # Basic ANSI color codes
    COLORS = {
        '30': 'black',
        '31': 'red',
        '32': 'green',
        '33': 'yellow',
        '34': 'blue',
        '35': 'magenta',
        '36': 'cyan',
        '37': 'white',
        '90': 'gray',
        '91': 'red',
        '92': 'green',
        '93': 'yellow',
        '94': 'blue',
        '95': 'magenta',
        '96': 'cyan',
        '97': 'white',
    }

    # Text attributes
    ATTRIBUTES = {
        '1': 'bold',
        '3': 'italic',
        '4': 'underline',
    }

    def __init__(self, text_widget):
        self.text = text_widget
        self.init_tags()

    def init_tags(self):
        """Initialize text widget tags for ANSI colors and attributes"""
        # Define color tags
        for code, color in self.COLORS.items():
            self.text.tag_configure(f"fg_{code}", foreground=color)
            # Background colors (40-47, 100-107)
            bg_code = str(int(code) + 10)
            self.text.tag_configure(f"bg_{bg_code}", background=color)

        # Define attribute tags
        self.text.tag_configure('bold', font=('TkDefaultFont', 10, 'bold'))
        self.text.tag_configure('italic', font=('TkDefaultFont', 10, 'italic'))
        self.text.tag_configure('underline', underline=1)

        # Reset tag (default formatting)
        self.text.tag_configure('reset', foreground='black', background='white')

    def process_text(self, text):
        """Process text with ANSI escape codes and add to text widget with appropriate styling"""
        # Split the text by ANSI escape sequences
        parts = self.ANSI_PATTERN.split(text)

        # Track active tags
        active_tags = set()

        # Process each part
        i = 0
        while i < len(parts):
            if i % 3 == 0:  # This is regular text
                if parts[i]:
                    # Insert text with current active tags
                    self.text.insert(tk.END, parts[i], tuple(active_tags) if active_tags else '')
            else:
                if i % 3 == 1:  # This is the parameter part
                    if parts[i] and parts[i+1] == 'm':  # 'm' is for SGR (Select Graphic Rendition)
                        codes = parts[i].split(';')
                        for code in codes:
                            if code == '0':  # Reset
                                active_tags.clear()
                            elif code in self.COLORS:  # Foreground color
                                # Remove existing foreground colors
                                active_tags = {tag for tag in active_tags if not tag.startswith('fg_')}
                                active_tags.add(f"fg_{code}")
                            elif code.startswith('4') and code[1:] in self.COLORS:  # Background color
                                # Remove existing background colors
                                active_tags = {tag for tag in active_tags if not tag.startswith('bg_')}
                                active_tags.add(f"bg_{code}")
                            elif code in self.ATTRIBUTES:  # Text attribute
                                active_tags.add(self.ATTRIBUTES[code])
                i += 1  # Skip the command part
            i += 1


class ToolTip:
    """Create a tooltip for a given widget with delayed show/hide"""
    def __init__(self, widget, delay=500):
        self.widget = widget
        self.delay = delay
        self.tip_window = None
        self.id = None
        self.text = ''
        self.x = self.y = 0

        # Bind events
        self.widget.bind('<Enter>', self.enter)
        self.widget.bind('<Leave>', self.leave)
        self.widget.bind('<Motion>', self.motion)

        # For combobox, add special binding for showing tooltip when dropdown opens
        if isinstance(widget, ttk.Combobox):
            widget.bind('<<ComboboxSelected>>', self.update_tooltip)

    def enter(self, event=None):
        """Schedule showing the tooltip"""
        self.schedule()

    def leave(self, event=None):
        """Cancel showing tooltip and hide if visible"""
        self.unschedule()
        self.hide()

    def motion(self, event=None):
        """Update position and reschedule tooltip"""
        self.x = event.x
        self.y = event.y
        self.unschedule()
        self.schedule()

    def schedule(self):
        """Schedule showing the tooltip"""
        self.unschedule()
        self.id = self.widget.after(self.delay, self.show)

    def unschedule(self):
        """Unschedule showing the tooltip"""
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def show(self):
        """Show the tooltip"""
        if self.tip_window or not self.text:
            return

        # Get widget position
        x = self.widget.winfo_rootx() + self.x + 20
        y = self.widget.winfo_rooty() + self.y + 20

        # Create tooltip window
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # Remove window decorations

        # Position tooltip
        tw.wm_geometry(f"+{x}+{y}")

        # Create tooltip content
        label = ttk.Label(tw, text=self.text, justify=tk.LEFT,
                          background="#ffffe0", relief=tk.SOLID, borderwidth=1)
        label.pack(padx=2, pady=2)

    def hide(self):
        """Hide the tooltip"""
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

    def update_tooltip(self, event=None):
        """Update tooltip text based on current widget value"""
        if hasattr(self.widget, 'get'):
            self.text = self.widget.get()


class SerialGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Interface GUI")
        self.root.geometry("1000x900")  # Increased height to accommodate new elements
        self.root.minsize(800, 600)     # Increased minimum size as well

        self.serial_port = None
        self.is_reading = False
        self.read_thread = None

        # Calculate initial dimensions
        self.initial_width = 1000
        self.right_pane_width = int(self.initial_width * 0.25)  # 1/4 of the window width

        self.create_widgets()
        self.refresh_ports()

    def _set_combobox_width(self, combobox, extra_width=0):
        """Set the width of a combobox based on the longest item in its list"""
        values = combobox['values']
        if not values:
            return

        # Find the longest item
        max_length = max(len(str(item)) for item in values)

        # Add a small buffer for visual comfort and extra_width for specific adjustments
        combobox.config(width=max_length + 1 + extra_width)

    def create_widgets(self):
        # Create frame for controls
        control_frame = ttk.LabelFrame(self.root, text="Connection Settings")
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # Serial port selection
        ttk.Label(control_frame, text="Serial Port:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.port_combo = ttk.Combobox(control_frame)  # Width will be set after values are loaded
        self.port_combo.grid(row=0, column=1, padx=5, pady=5)
        self.port_combo.bind("<<ComboboxSelected>>", self.update_port_tooltip)

        # Create tooltip for port combo
        self.port_tooltip = ToolTip(self.port_combo)

        refresh_btn = ttk.Button(control_frame, text="Refresh", command=self.refresh_ports)
        refresh_btn.grid(row=0, column=2, padx=5, pady=5)

        # Baud rate selection
        ttk.Label(control_frame, text="Baud Rate:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.baud_combo = ttk.Combobox(control_frame, values=["9600", "19200", "38400", "57600", "115200", "460800"])
        self._set_combobox_width(self.baud_combo)
        self.baud_combo.current(4)  # Default to 115200
        self.baud_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # Log level selection
        ttk.Label(control_frame, text="Log Level:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.log_level_combo = ttk.Combobox(control_frame, values=["Debug", "Info", "Warning", "Error", "Critical", "None"])
        self._set_combobox_width(self.log_level_combo)
        self.log_level_combo.current(3)  # Default to Error
        self.log_level_combo.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        self.log_level_combo.bind("<<ComboboxSelected>>", self.set_log_level)

        # Connection buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=5)

        self.connect_btn = ttk.Button(btn_frame, text="Connect", command=self.open_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=5)

        self.disconnect_btn = ttk.Button(btn_frame, text="Disconnect", command=self.close_connection, state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT, padx=5)

        # Status bar at the bottom of the window
        self.status_var = tk.StringVar()
        self.status_var.set("Not connected")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Create a PanedWindow to hold Serial Output and File Operations side by side
        self.main_paned_window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED,
                                              sashwidth=4, showhandle=True)
        self.main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # LEFT SIDE: Serial Outpu
        display_frame = ttk.LabelFrame(self.main_paned_window, text="Serial Output")

        # Display options
        options_frame = ttk.Frame(display_frame)
        options_frame.pack(fill=tk.X, padx=5, pady=2)

        # Timestamp option
        self.timestamp_var = tk.BooleanVar(value=False)
        self.timestamp_cb = ttk.Checkbutton(options_frame, text="Show Timestamps", variable=self.timestamp_var)
        self.timestamp_cb.pack(side=tk.LEFT, padx=5)

        # Hex display option
        self.hexview_var = tk.BooleanVar(value=False)
        self.hexview_cb = ttk.Checkbutton(options_frame, text="Hex Display", variable=self.hexview_var)
        self.hexview_cb.pack(side=tk.LEFT, padx=5)

        # Create a scrolled text widget for output display
        self.output_text = scrolledtext.ScrolledText(display_frame, wrap=tk.WORD, width=60, height=15)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.output_text.config(state=tk.DISABLED)

        # Add input area for sending data
        input_frame = ttk.Frame(display_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(input_frame, text="Send:").pack(side=tk.LEFT, padx=2)

        self.input_text = ttk.Entry(input_frame, width=50)
        self.input_text.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.input_text.bind("<Return>", self.send_data)  # Send data when Enter key is pressed
        self.input_text.config(state=tk.DISABLED)

        # Add checkbox for newline option
        self.newline_var = tk.BooleanVar(value=True)
        self.newline_cb = ttk.Checkbutton(input_frame, text="Add CR+LF", variable=self.newline_var)
        self.newline_cb.pack(side=tk.RIGHT, padx=2)

        # Add checkbox for hex input
        self.hexinput_var = tk.BooleanVar(value=False)
        self.hexinput_cb = ttk.Checkbutton(input_frame, text="Hex Input", variable=self.hexinput_var)
        self.hexinput_cb.pack(side=tk.RIGHT, padx=2)

        self.send_btn = ttk.Button(input_frame, text="Send", command=self.send_data, state=tk.DISABLED)
        self.send_btn.pack(side=tk.RIGHT, padx=5)

        # Initialize ANSI colorizer
        self.ansi_colorizer = AnsiColorizer(self.output_text)

        # RIGHT SIDE: File Operations
        file_operations_frame = ttk.LabelFrame(self.main_paned_window, text="File Operations")

        # Create a frame for buttons to be on the same line
        buttons_frame = ttk.Frame(file_operations_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)

        # Button to select and open a text file
        self.open_file_btn = ttk.Button(buttons_frame, text="Open File", command=self.open_text_file, width=0)
        self.open_file_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Clear button
        self.clear_file_btn = ttk.Button(buttons_frame, text="Clear", command=self.clear_file_content, width=0)
        self.clear_file_btn.pack(side=tk.LEFT, padx=0)

        # Label for showing selected file
        self.file_path_var = tk.StringVar(value="No file selected")
        self.file_path_label = ttk.Label(file_operations_frame, textvariable=self.file_path_var, anchor=tk.W, wraplength=200)
        self.file_path_label.pack(padx=5, pady=5, fill=tk.X)

        # Text content frame
        file_content_frame = ttk.LabelFrame(file_operations_frame, text="File Content")
        file_content_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=5)

        # Scrolled text for file content - width will be automatically adjusted based on PanedWindow
        self.file_content_text = scrolledtext.ScrolledText(file_content_frame, wrap=tk.WORD, height=10)
        self.file_content_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.file_content_text.bind("<Button-1>", self.highlight_line)  # Bind single-click to highlight
        self.file_content_text.bind("<Double-Button-1>", self.send_current_line)  # Bind double-click event
        self.file_content_text.bind("<Control-s>", self.send_file_content)  # Bind Ctrl+S to send entire file

        # Instructions label
        self.instruction_label = ttk.Label(file_content_frame, text="Click on a line to highlight it.\nDouble-click on a line to send it to the serial port when connected.\nPress Ctrl+S to send the entire file.")
        self.instruction_label.pack(side=tk.BOTTOM, padx=5, pady=2)

        # Bind event to update wraplength when window size changes
        self.root.bind("<Configure>", self._update_wraplength)

        # Add both frames to the PanedWindow with appropriate initial sizes
        self.main_paned_window.add(display_frame, stretch="always", minsize=300)
        self.main_paned_window.add(file_operations_frame, stretch="never", minsize=200)

        # Set initial position of sash after the window is fully created
        self.root.update_idletasks()
        self.root.after(100, self._set_initial_sash_position)

    def _set_initial_sash_position(self):
        """Set the initial position of the sash divider after window is drawn"""
        window_width = self.root.winfo_width()
        if window_width < 100:  # Window not fully created yet
            window_width = self.initial_width
        sash_position = int(window_width * 0.75)  # Place sash at 75% of the window width
        try:
            self.main_paned_window.sash_place(0, sash_position, 0)
        except:
            # Retry once if there's an issue
            self.root.after(200, self._set_initial_sash_position)

    def refresh_ports(self):
        """Refresh the list of available serial ports"""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports

        # Set the width based on the longest port name, with a minimum of 10 characters
        # and maximum of 15 characters to prevent overly wide combobox
        if ports:
            max_length = min(max(len(port) for port in ports), 15)
            self.port_combo.config(width=max(max_length, 10))
            self.port_combo.current(0)
            # Update port tooltip with current selection
            self.port_tooltip.text = self.port_combo.get()
        else:
            self.port_combo.config(width=10)  # Default width if no ports
            self.status_var.set("No serial ports found")

    def update_port_tooltip(self, event=None):
        """Update the tooltip for the port combo box with the current selection"""
        current_port = self.port_combo.get()
        if current_port:
            self.port_tooltip.text = current_por

    def set_log_level(self, event=None):
        """Set the logging level based on the selected value"""
        level_str = self.log_level_combo.get()
        level_map = {
            "Debug": LogLevel.DEBUG,
            "Info": LogLevel.INFO,
            "Warning": LogLevel.WARNING,
            "Error": LogLevel.ERROR,
            "Critical": LogLevel.CRITICAL,
            "None": LogLevel.NONE
        }
        level = level_map.get(level_str, LogLevel.INFO)
        logger.set_level(level)
        logger.info(f"Log level set to {level_str}")

    def open_connection(self):
        """Open the selected serial connection"""
        port = self.port_combo.get()
        if not port:
            self.status_var.set("Error: No port selected")
            logger.error("No port selected")
            return

        try:
            baud_rate = int(self.baud_combo.get())
            self.serial_port = serial.Serial(port, baud_rate, timeout=1)
            self.status_var.set(f"Connected to {port} at {baud_rate} baud")
            logger.info(f"Connected to {port} at {baud_rate} baud")

            # Update button states
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            self.input_text.config(state=tk.NORMAL)
            self.send_btn.config(state=tk.NORMAL)

            # Start reading from the por
            self.is_reading = True
            self.read_thread = threading.Thread(target=self.read_serial, daemon=True)
            self.read_thread.start()

        except ValueError:
            self.status_var.set("Error: Invalid baud rate")
            logger.error("Invalid baud rate")
        except serial.SerialException:
            self.status_var.set(f"Error: Could not open port {port}")
            logger.error(f"Could not open port {port}")

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
            self.input_text.config(state=tk.DISABLED)
            self.send_btn.config(state=tk.DISABLED)

            self.status_var.set("Disconnected")
            logger.info("Disconnected from serial port")

    def read_serial(self):
        """Read data from the serial port in a separate thread"""
        while self.is_reading and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    if data:
                        # Debug log received data with escape characters in readable form
                        debug_str = repr(data.decode('utf-8', errors='replace'))
                        logger.debug(f"Serial received: {debug_str}")

                        self.display_data(data)
            except serial.SerialException:
                logger.error("Serial port disconnected unexpectedly")
                self.root.after(0, self.handle_disconnect)
                break
            time.sleep(0.1)

    def display_data(self, data):
        """Display received data in the text widget"""
        try:
            # Get current timestamp if enabled
            timestamp = ""
            if self.timestamp_var.get():
                now = datetime.datetime.now()
                timestamp = f"[{now.strftime('%H:%M:%S.%f')[:-3]}] "

            # Handle hex display if enabled
            if self.hexview_var.get():
                # Format as hex
                hex_data = binascii.hexlify(data).decode('ascii')
                # Format hex in pairs with spaces
                formatted_hex = ' '.join(hex_data[i:i+2] for i in range(0, len(hex_data), 2))
                display_text = timestamp + formatted_hex
                self.root.after(0, self._update_display, display_text)
            else:
                # Normal text display
                text = data.decode('utf-8', errors='replace')

                # Remove carriage returns (\r) from the text before processing
                text = text.replace('\r', '')

                # Process text by preserving exact newline positions
                # but still handling timestamps and empty line filtering
                if timestamp:
                    # Split strictly at newline characters to preserve line structure
                    lines = text.split('\n')
                    result = []
                    for i, line in enumerate(lines):
                        # Skip empty lines
                        if line.strip():
                            # Add a newline after each line except the last one
                            if i < len(lines) - 1:
                                result.append(timestamp + line + '\n')
                            else:
                                result.append(timestamp + line)
                    text = ''.join(result)
                else:
                    # If no timestamp, filter empty lines while preserving line structure
                    lines = text.split('\n')
                    result = []
                    for i, line in enumerate(lines):
                        if line.strip():
                            # Add a newline after each line except the last one
                            if i < len(lines) - 1:
                                result.append(line + '\n')
                            else:
                                result.append(line)
                    text = ''.join(result)

                self.root.after(0, self._update_display, text)
        except Exception as e:
            self.root.after(0, self._update_display, f"[Error displaying data: {e}]")

    def _update_display(self, text):
        """Update the display text (called from the main thread)"""
        self.output_text.config(state=tk.NORMAL)
        self.ansi_colorizer.process_text(text)
        # Auto-scroll to end
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)

    def handle_disconnect(self):
        """Handle unexpected disconnection"""
        self.status_var.set("Error: Serial port disconnected unexpectedly")
        self.close_connection()

    def send_data(self, event=None):
        """Send data over the serial port"""
        if self.serial_port and self.serial_port.is_open:
            input_text = self.input_text.get()
            if not input_text:
                return

            try:
                # Process input based on hex mode
                if self.hexinput_var.get():
                    # Process hex string (remove spaces, validate, convert to bytes)
                    hex_text = input_text.replace(' ', '')
                    # Validate hex string (must be even length and valid hex chars)
                    if len(hex_text) % 2 != 0:
                        self.status_var.set("Error: Hex string must have an even number of characters")
                        logger.error("Invalid hex string (odd length)")
                        return

                    # Check if string contains only valid hex characters
                    if not all(c in '0123456789ABCDEFabcdef' for c in hex_text):
                        self.status_var.set("Error: Invalid hex characters")
                        logger.error("Invalid hex characters in input")
                        return

                    # Convert hex to bytes
                    data = binascii.unhexlify(hex_text)
                    logger.debug(f"Sending hex data: {hex_text}")
                else:
                    # Regular text mode
                    data = input_text
                    # Add newline if option is selected
                    if self.newline_var.get():
                        data += '\r\n'
                    data = data.encode('utf-8')

                # Send data
                self.serial_port.write(data)
                logger.debug(f"Serial sent: {repr(data)}")
                self.input_text.delete(0, tk.END)

            except Exception as e:
                self.status_var.set(f"Error sending data: {str(e)}")
                logger.error(f"Error sending data: {str(e)}")

    def update_port_tooltip(self, event=None):
        """Update the tooltip for the port combo box with the current selection"""
        current_port = self.port_combo.get()
        if current_port:
            self.port_tooltip.text = current_port

    def open_text_file(self):
        """Open a text file dialog and display the content in the text box"""
        file_path = filedialog.askopenfilename(
            title="Select Text File",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )

        if not file_path:
            return  # User cancelled the operation

        try:
            # Update file path display
            self.file_path_var.set(file_path)

            # Read and display file content with utf-8 encoding
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                content = file.read()

                # Clear the text box and insert new conten
                self.file_content_text.config(state=tk.NORMAL)  # Temporarily enable editing
                self.file_content_text.delete(1.0, tk.END)
                # Make sure to remove any existing highlight tags as well
                self.file_content_text.tag_remove("highlight", "1.0", tk.END)
                self.file_content_text.insert(tk.END, content)
                self.file_content_text.config(state=tk.DISABLED)  # Set to read-only

            logger.info(f"Opened file: {file_path}")
            self.status_var.set(f"File opened: {file_path}")

        except Exception as e:
            error_msg = f"Error opening file: {str(e)}"
            self.file_content_text.config(state=tk.NORMAL)  # Temporarily enable editing
            self.file_content_text.delete(1.0, tk.END)
            self.file_content_text.insert(tk.END, error_msg)
            self.file_content_text.config(state=tk.DISABLED)  # Set to read-only
            self.status_var.set(error_msg)
            logger.error(error_msg)

    def send_file_content(self, event=None):
        """Send the content of the file text box to the serial port"""
        if not self.serial_port or not self.serial_port.is_open:
            self.status_var.set("Error: Not connected to any serial port")
            return

        content = self.file_content_text.get(1.0, tk.END)
        if not content.strip():
            self.status_var.set("Error: No content to send")
            return

        try:
            # Send content to serial port
            data = content.encode('utf-8')
            self.serial_port.write(data)
            logger.info(f"Sent file content to serial port: {len(data)} bytes")
            self.status_var.set(f"File content sent: {len(data)} bytes")
        except Exception as e:
            error_msg = f"Error sending file content: {str(e)}"
            self.status_var.set(error_msg)
            logger.error(error_msg)

    def update_port_tooltip(self, event=None):
        """Update the tooltip for the port combo box with the current selection"""
        current_port = self.port_combo.get()
        if current_port:
            self.port_tooltip.text = current_port

    def clear_file_content(self):
        """Clear the file content text box"""
        self.file_content_text.config(state=tk.NORMAL)  # Temporarily enable editing
        self.file_content_text.delete(1.0, tk.END)
        # Make sure to remove any existing highlight tags as well
        self.file_content_text.tag_remove("highlight", "1.0", tk.END)
        self.file_content_text.config(state=tk.DISABLED)  # Set back to read-only
        self.file_path_var.set("No file selected")
        logger.info("File content cleared")

    def _update_wraplength(self, event=None):
        """Update wraplength of labels based on the current window size"""
        # Only respond to window size changes, not all configure events
        if event and event.widget == self.root:
            # Get the current width of the file operations pane
            sash_pos = self.main_paned_window.sash_coord(0)[0]
            window_width = self.root.winfo_width()
            file_pane_width = window_width - sash_pos - 20  # Some padding

            # Update wraplength for our labels
            if hasattr(self, 'file_path_label'):
                self.file_path_label.config(wraplength=max(100, file_pane_width - 20))
            if hasattr(self, 'instruction_label'):
                self.instruction_label.config(wraplength=max(100, file_pane_width - 20))

    def send_current_line(self, event=None):
        """Send the current line (where cursor is) to the serial port"""
        if not self.serial_port or not self.serial_port.is_open:
            self.status_var.set("Error: Not connected to any serial port")
            return

        try:
            # Get the current line based on cursor position
            index = self.file_content_text.index(f"@{event.x},{event.y}")
            line_start = self.file_content_text.index(f"{index} linestart")
            line_end = self.file_content_text.index(f"{index} lineend")
            line_content = self.file_content_text.get(line_start, line_end)

            if not line_content.strip():
                return  # Skip empty lines

            # Prepare data for sending
            data = line_content

            # Add newline if option is selected
            if self.newline_var.get():
                data += '\r\n'

            # Encode and send
            data = data.encode('utf-8')
            self.serial_port.write(data)

            # Report in status bar
            self.status_var.set(f"Sent line: {line_content[:40]}{'...' if len(line_content) > 40 else ''}")
            logger.info(f"Sent line to serial port: {line_content}")

            # Highlight the sent line (without auto-removal)
            self.file_content_text.tag_remove("highlight", "1.0", tk.END)
            self.file_content_text.tag_configure("highlight", background="lightblue")
            self.file_content_text.tag_add("highlight", line_start, line_end)

        except Exception as e:
            error_msg = f"Error sending line: {str(e)}"
            self.status_var.set(error_msg)
            logger.error(error_msg)

    def highlight_line(self, event=None):
        """Highlight the line that was clicked on"""
        try:
            # Clear any existing highlights
            self.file_content_text.tag_remove("highlight", "1.0", tk.END)

            # Get the current line based on cursor position
            index = self.file_content_text.index(f"@{event.x},{event.y}")
            line_start = self.file_content_text.index(f"{index} linestart")
            line_end = self.file_content_text.index(f"{index} lineend")

            # Highlight the clicked line
            self.file_content_text.tag_configure("highlight", background="lightblue")
            self.file_content_text.tag_add("highlight", line_start, line_end)

            # Make the clicked line visible (especially if scrolled out of view)
            self.file_content_text.see(index)

        except Exception as e:
            logger.error(f"Error highlighting line: {str(e)}")

    def update_port_tooltip(self, event=None):
        """Update the tooltip for the port combo box with the current selection"""
        current_port = self.port_combo.get()
        if current_port:
            self.port_tooltip.text = current_port


if __name__ == "__main__":
    root = tk.Tk()
    app = SerialGUI(root)
    root.mainloop()