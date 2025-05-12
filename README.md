# PySerialUI

A Python GUI application for serial port communication.

## Features

- Select available serial ports from a dropdown list
- Choose baud rate (9600, 115200, 460800) or enter a custom value
- Connect/disconnect to serial ports
- Display incoming serial data in real-time
- Optional timestamp display with microsecond resolution
- Optional hex display of received data
- Send commands to the connected device
  - Option to automatically add CR+LF (carriage return and line feed) to sent commands
  - Option to send data as hexadecimal bytes
- Open and view text files
  - Select and open text files through a file dialog
  - Edit text in the file viewer
  - Send file content to the serial port
- Multiple log levels for debugging (Debug, Info, Warning, Error, Critical, None)
- Automatically refresh port list

## Requirements

- Python 3.6 or higher
- PySerial library
- tkinter (usually comes with Python)

## Installation

### Standard Installation

1. Make sure you have Python installed
2. Install required libraries:

```bash
pip3 install pyserial
```

### Using a Virtual Environment (Recommended)

Setting up a virtual environment keeps your dependencies isolated and avoids conflicts with other Python projects:

1. Make sure you have Python 3.6+ installed
2. Create a virtual environment:

```bash
# Navigate to the project directory
cd /path/to/PySerialUI

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

3. Install required dependencies:

```bash
# Make sure you're in the activated virtual environment (you'll see "(venv)" in your terminal)
pip install -r requirements.txt
# Or install directly:
# pip install pyserial
```

## Usage

### Standard Usage

Run the application:

```bash
python3 serial_gui.py
```

### With Virtual Environment

If you're using a virtual environment:

```bash
# Make sure the virtual environment is activated (you'll see "(venv)" in your terminal)
# Then run:
python serial_gui.py
```

### Instructions

1. Select a serial port from the dropdown menu
2. Choose a baud rate (default is 115200)
3. Select the desired log level (Debug shows all messages, None disables logging)
4. Click "Connect" to establish a connection
5. The output window will display incoming data
   - Toggle "Show Timestamps" to add timestamps to each line
   - Toggle "Hex Display" to view data in hexadecimal format
6. To send data, type in the input field and press Enter or click "Send"
7. Check/uncheck "Add CR+LF" option to control whether carriage return and line feed characters are added to sent messages
8. Enable "Hex Input" to send data as hexadecimal bytes:
   - Enter hex values (e.g., "48656C6C6F" for "Hello")
   - Spaces are automatically removed
   - Input must contain only valid hex characters (0-9, A-F)
   - Input must have an even number of characters
9. To work with text files:
   - Click "Open Text File" to select and open a text file
   - The file content will be displayed in the read-only text box
   - Double-click on a line to send just that line to the serial port
   - Click "Send to Serial" to send the entire text to the connected serial device
   - Click "Clear" to clear the text box
10. Click "Disconnect" to close the connection

## Notes

- The application uses threading to prevent UI freezing while reading serial data
- All received data is displayed in the scrollable text area
- UTF-8 encoding is used by default to display received data
- Empty lines are filtered out from the display for cleaner output
- Newline characters (\n) in the serial data are strictly preserved to maintain the original line structure
- Timestamp display shows time in HH:MM:SS.mmm format (millisecond precision) for non-empty lines only
- Hex display shows bytes in space-separated hex pairs
- Log levels control what debug information is printed to the console:
  - Debug: All messages including detailed I/O data
  - Info: General information, connections, disconnections
  - Warning: Issues that don't prevent operation
  - Error: Serious problems that prevent certain operations
  - Critical: Fatal errors that might crash the application
  - None: Disable all logging