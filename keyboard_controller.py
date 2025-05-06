import hid
import time
import logging

# Update logging configuration to use INFO level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class KeyboardController:
    def __init__(self):
        self.vendor_id = 0x258A
        self.product_id = 0x0049
        self.device = None
        self.packet_header = [0x08, 0x0A, 0x7A, 0x01]
        self.packet_length = 382
        self.connected = False
        
        # Add keyboard layout definition for packet creation
        self.layout_def = [
            ["Esc", "`", "Tab", "Caps", "Shift", "Ctrl"],
            ["F1", "1", "Q", "A", "Z", "Win"],
            ["F2", "2", "W", "S", "X", "Alt"],
            ["F3", "3", "E", "D", "C", "NAN"],
            ["F4", "4", "R", "F", "V", "NAN"],
            ["F5", "5", "T", "G", "B", "Space"],
            ["F6", "6", "Y", "H", "N", "NAN"],
            ["F7", "7", "U", "J", "M", "NAN"],
            ["F8", "8", "I", "K", ",", "Alt"],
            ["F9", "9", "O", "L", ".", "Fn"],
            ["F10", "0", "P", ";", "/", "Ctrl"],
            ["F11", "-", "[", "'", "NAN", "NAN"],
            ["F12", "=", "]", "NAN", "NAN", "NAN"],
            ["PrtSc", "Bksp", "\\", "Enter", "Shift", "←"],
            ["Pause", "NAN", "NAN", "NAN", "↑", "↓"],
            ["Del", "Home", "End", "PgUp", "PgDn", "→"]
        ]
        
        logger.debug(f"KeyboardController initialized with VID:{self.vendor_id:04x} PID:{self.product_id:04x}")
        
    def connect(self):
        try:
            logger.info(f"Attempting to connect to keyboard with VID:{self.vendor_id:04x} PID:{self.product_id:04x}")
            
            # Find all HID devices
            found_devices = hid.enumerate(self.vendor_id, self.product_id)
            logger.info(f"Found {len(found_devices)} matching devices")
            
            target_device = None
            for device in found_devices:
                # Log details about each found device
                logger.info(f"Device: Path={device['path']}, Interface={device.get('interface_number', 'N/A')}, "
                          f"Usage={device.get('usage', 'N/A')}, Usage Page={device.get('usage_page', 'N/A')}")
                
                # Look for the specific interface with Usage Page 0xFF00 (vendor defined) and Usage 0x0001
                # This appears to be the LED control interface
                if device.get('usage_page') == 0xFF00 and device.get('usage') == 0x0001:
                    target_device = device
                    logger.info(f"Found target device with LED control interface")
                    break
            
            if target_device:
                # Open the specific device by path
                self.device = hid.device()
                self.device.open_path(target_device['path'])
                self.device.set_nonblocking(1)
                self.connected = True
                
                # Get more device info if available
                try:
                    manufacturer = self.device.get_manufacturer_string()
                    product = self.device.get_product_string()
                    serial = self.device.get_serial_number_string()
                    logger.info(f"Connected to device: Manufacturer: {manufacturer}, Product: {product}, Serial: {serial}")
                except:
                    logger.info(f"Connected to device {self.vendor_id:04x}:{self.product_id:04x} (no extended info available)")
                    
                return True
            else:
                # Fall back to default connection method if specific interface not found
                logger.warning("Could not find the specific LED control interface, falling back to default")
                self.device = hid.device()
                self.device.open(self.vendor_id, self.product_id)
                self.device.set_nonblocking(1)
                self.connected = True
                logger.info(f"Connected to device using default interface")
                return True
                
        except Exception as e:
            logger.error(f"Failed to connect to the keyboard: {e}", exc_info=True)
            self.connected = False
            return False
    
    def disconnect(self):
        if self.device:
            logger.info(f"Disconnecting from keyboard VID:{self.vendor_id:04x} PID:{self.product_id:04x}")
            self.device.close()
            self.connected = False
            logger.info("Disconnected from the keyboard")
    
    def send_led_config(self, key_colors, intensity=1.0):
        """
        Send LED configuration packet to the keyboard
        
        Args:
            key_colors: Either a list of RGB tuples or a ConfigManager memory map
            intensity: Float between 0.0 and 1.0 to scale brightness
        """
        if not self.connected:
            if not self.connect():
                return False
        
        # Fix: Ensure intensity is properly bounded between 0.01 and 1.0
        # (avoid 0.0 which would make all keys black)
        intensity = max(0.01, min(1.0, intensity))
        
        # Check if we're using a memory map (faster)
        if isinstance(key_colors, memoryview):
            # Create packet directly from memory map
            packet = bytearray(self.packet_header)
            
            # Add colors directly from memory map, adjusting for intensity
            color_idx = 0
            
            # Process layout definition in order
            for row in self.layout_def:
                for key in row:
                    if key == "NAN":
                        # Add zeros for NAN positions
                        packet.extend([0, 0, 0])
                    else:
                        # Get color from memory map
                        if color_idx < 126:
                            # Fix: Use direct calculation with proper rounding and bounds checking
                            r = min(255, max(0, int(key_colors[color_idx*3] * intensity)))
                            g = min(255, max(0, int(key_colors[color_idx*3+1] * intensity)))
                            b = min(255, max(0, int(key_colors[color_idx*3+2] * intensity)))
                            packet.extend([r, g, b])
                            color_idx += 1
                        else:
                            packet.extend([0, 0, 0])
            
            # Add padding to reach required length (important!)
            padding_needed = max(0, self.packet_length - len(packet))
            if padding_needed > 0:
                while len(packet) < self.packet_length:
                    packet.extend([0, 0, 0])
            
            # Ensure packet is exactly the required length
            if len(packet) != self.packet_length:
                packet = packet[:self.packet_length]
        else:
            # Use the traditional method
            packet = self.create_packet(key_colors, intensity)
        
        try:
            # Send as feature report
            self.device.send_feature_report(packet)
            return True
        except Exception as e:
            logger.error(f"Error sending feature report: {e}")
            self.disconnect()
            return False
    
    def create_packet(self, key_colors, intensity=1.0):
        """
        Create the LED configuration packet with proper NAN values
        
        Args:
            key_colors: List of RGB tuples (r, g, b) for each key (excluding NANs)
            intensity: Float between 0.0 and 1.0 to scale all colors
        
        Returns:
            bytearray: The complete packet to send
        """
        packet = bytearray(self.packet_header)
        logger.debug(f"Packet header: {' '.join([f'{b:02X}' for b in self.packet_header])}")
        
        # Apply intensity to colors
        adjusted_colors = []
        for r, g, b in key_colors:
            # Scale the colors by intensity (0-255 * intensity) with proper bounds checking
            adj_r = min(255, max(0, int(r * intensity)))
            adj_g = min(255, max(0, int(g * intensity)))
            adj_b = min(255, max(0, int(b * intensity)))
            adjusted_colors.append((adj_r, adj_g, adj_b))
        
        # Current key color index
        color_idx = 0
        
        # Go through layout definition in order, row by row
        for row in self.layout_def:
            for key in row:
                if key == "NAN":
                    # Add 00 00 00 for NAN positions
                    packet.extend([0, 0, 0])
                    logger.debug(f"Added NAN position: 00 00 00")
                else:
                    # Add color for real key
                    if color_idx < len(adjusted_colors):
                        r, g, b = adjusted_colors[color_idx]
                        packet.extend([r, g, b])
                        # Log every 10th key to reduce logging volume
                        if color_idx % 10 == 0:
                            logger.debug(f"Added key {color_idx} ({key}): R:{r:02X} G:{g:02X} B:{b:02X}")
                        color_idx += 1
                    else:
                        # Safety - if we run out of colors, pad with zeros
                        packet.extend([0, 0, 0])
        
        # Pad to reach required length
        padding_needed = max(0, self.packet_length - len(packet))
        if padding_needed > 0:
            logger.debug(f"Adding {padding_needed} bytes of padding to reach required length of {self.packet_length}")
            while len(packet) < self.packet_length:
                packet.extend([0, 0, 0])
        
        # Ensure the packet is exactly the required length
        if len(packet) != self.packet_length:
            logger.warning(f"Packet length {len(packet)} differs from required {self.packet_length}, truncating")
            packet = packet[:self.packet_length]
            
        logger.debug(f"Final packet length: {len(packet)} bytes")
        return packet 