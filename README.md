# PySerialUI

A Python GUI application for serial port communication.

## Features

- Select available serial ports from a dropdown list
- Choose baud rate (9600, 115200, 460800) or enter a custom value
- Connect/disconnect to serial ports
- Display incoming serial data in real-time
- Automatically refresh port list

## Requirements

- Python 3.6 or higher
- PySerial library
- tkinter (usually comes with Python)

## Installation

1. Make sure you have Python installed
2. Install required libraries:

```bash
pip3 install pyserial
```

## Usage

Run the application:

```bash
python3 serial_gui.py
```

### Instructions

1. Select a serial port from the dropdown menu
2. Choose a baud rate (default is 115200)
3. Click "Connect" to establish a connection
4. The output window will display incoming data
5. Click "Disconnect" to close the connection

## Notes

- The application uses threading to prevent UI freezing while reading serial data
- All received data is displayed in the scrollable text area
- UTF-8 encoding is used by default to display received data