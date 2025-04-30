# Keyboard LED Editor

A Python GUI application to customize and control the LED lighting on Redgradon keybaord only, specifically 
for keyboards with vendor ID 258A and product ID 0049.


Note: I only made this because OpenRGB didn't support redgraon keybaord. It only has basic UI. Feel free to change UI or add features.

## Features
This uses direct mode in Redragon keybaord to change the LED lightening.

- Visual keyboard layout representation
- Color picker for individual keys
- Preset color schemes
- Function key highlighting
- Rainbow color effect
- Brightness/intensity control
- Configuration saving and loading
- Hot-reload support
- Device information display

## Requirements

- Python 3.6 or higher
- USB keyboard with RGB support (vendor ID: 258A, product ID: 0049)
- Linux, macOS, or Windows operating system

## Installation

1. Clone this repository or download the source code:

```bash
git clone https://github.com/evansunde/sinodragon.git
```

2. Install the required dependencies:

Note: On Linux, you may need to install additional libraries for USB access:

Set up udev rules (Linux only):

Create a file /etc/udev/rules.d/99-keyboard.rules with the following content:

```bash
SUBSYSTEM=="usb", ATTRS{idVendor}=="258a", ATTRS{idProduct}=="0049", MODE="0666"
```
Then reload the rules:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

3. Run the application:

```bash
python main.py
```

## Usage

### Basic Controls

1. Connect to your keyboard: Click the "Connect" button to establish a connection with your keyboard.
2. Change individual key colors: Click on any key on the layout to open a color picker and set its color.
3. Quick color presets: Use the colored buttons at the bottom to quickly set all keys to a specific color.
4. Adjust brightness: Use the slider to control the overall brightness of the keyboard LEDs.
5. Apply changes: Click "Apply" to send the current configuration to the keyboard.
6. Auto-reload: Toggle this button to automatically apply changes as you make them.

### More Features

- Function keys: Click "Function Keys" to highlight all function keys (F1-F12) in orange.
- Rainbow effect: Click "Rainbow" to create a gradient effect across all keys.
- Device Info: Click "Device Info" to view information about the connected keyboard.
- Save configurations: Enter a name and click "Save" to store the current configuration for later use.
- Load configurations: Select a saved configuration from the dropdown to load it.

### Advanced Configuration

The application generates LED packets in the format required by the keyboard. The packet structure starts with a header 08 0A 7A 01 followed by RGB values for each key in a specific order. The application handles the NAN (not-a-key) positions in the layout by sending 00 00 00 for those positions.
You can modify the keyboard layout in keyboard_controller.py if you have a different keyboard model with a similar protocol but different layout.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue. I can only solve the issue in my free time.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

Thanks to the HIDAPI project for providing the USB HID interface
PyQt5 for the GUI framework
