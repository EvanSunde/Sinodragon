"""
Command-line interface functionality.
Handles command-line arguments and keyboard control from the terminal.
"""

import sys
import time
import argparse
import logging

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QColor

# Get the logger
logger = logging.getLogger(__name__)

class CommandLineInterface:
    @staticmethod
    def display_text_on_keyboard(keyboard_app_class, text, timeout=None, color=None, scroll=False, speed=0.5):
        """
        Display text on the keyboard LEDs
        
        Args:
            keyboard_app_class: The KeyboardConfigApp class
            text: The text to display on the keyboard
            timeout: Optional timeout in seconds to display the text
            color: RGB tuple or color name for the text
            scroll: Whether to scroll the text across the keyboard
            speed: Scroll speed (only used if scroll=True)
        """
        # Parse color if provided as string
        if isinstance(color, str):
            color_map = {
                "white": (255, 255, 255),
                "red": (255, 0, 0),
                "green": (0, 255, 0),
                "blue": (0, 0, 255),
                "yellow": (255, 255, 0),
                "cyan": (0, 255, 255),
                "magenta": (255, 0, 255),
                "orange": (255, 165, 0),
                "purple": (128, 0, 128)
            }
            color = color_map.get(color.lower(), (255, 255, 255))
        
        logger.info(f"Displaying text on keyboard: '{text}' " + 
                  f"(timeout: {timeout}s, {'scrolling' if scroll else 'static'}, " + 
                  f"color: {color})")
        
        app = QApplication(sys.argv)
        keyboard_app = keyboard_app_class()
        
        # Connect to keyboard
        if not keyboard_app.keyboard.connected:
            if not keyboard_app.keyboard.connect():
                logger.error("Failed to connect to keyboard")
                return False
        
        try:
            # Display the text on keyboard
            if scroll:
                keyboard_app.text_display.scroll_text(text, speed=speed, color=color)
            else:
                keyboard_app.text_display.display_text(text, color=color)
            
            if timeout:
                # Wait for the specified timeout
                logger.info(f"Waiting {timeout} seconds before restoring default config")
                time.sleep(timeout)
            else:
                # If no timeout, keep the app running
                logger.info("Text displayed on keyboard. Press Ctrl+C to exit.")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt received, exiting")
        except Exception as e:
            logger.error(f"Error displaying text: {e}")
        finally:
            # Restore default configuration and clean up
            keyboard_app.load_config()
            keyboard_app.send_config()
            logger.info("Restored default configuration")
            keyboard_app.keyboard.disconnect()
        
        return True
    
    @staticmethod
    def parse_arguments():
        """Parse command line arguments"""
        parser = argparse.ArgumentParser(description="Keyboard LED Configuration")
        
        # GUI mode
        parser.add_argument('--gui', action='store_true',
                           help='Launch the graphical user interface')
        
        # Text display options
        parser.add_argument('--text', '-t', type=str, 
                           help='Text to display on keyboard')
        
        parser.add_argument('--color', '-c', type=str, 
                           help='Color for the text (name or r,g,b)')
        
        parser.add_argument('--timeout', type=int, 
                           help='Timeout in seconds to display text before reverting to default')
        
        parser.add_argument('--scroll', '-s', action='store_true',
                           help='Scroll the text across the keyboard')
        
        parser.add_argument('--speed', type=float, default=0.5,
                           help='Scroll speed in seconds per position (default: 0.5)')
        
        # Configuration management
        parser.add_argument('--list-configs', action='store_true',
                           help='List all saved configurations')
        
        parser.add_argument('--load-config', type=str,
                           help='Load and apply a saved configuration')
        
        # Effects options
        parser.add_argument('--effect', type=str, 
                           choices=['rainbow', 'wave', 'function', 'breathe', 'ripple', 'gradient', 'reactive', 'spectrum', 'starlight'],
                           help='Apply a special effect to the keyboard')
        
        parser.add_argument('--effect-color', type=str,
                           help='Color for effects (when applicable)')
                           
        parser.add_argument('--effect-speed', type=float, default=0.1,
                           help='Speed of the effect animation (when applicable)')
        
        return parser.parse_args()
    
    @staticmethod
    def handle_command_line(keyboard_app_class):
        """Handle command line arguments and launch appropriate action"""
        args = CommandLineInterface.parse_arguments()
        
        # GUI launch mode
        if args.gui:
            # Return None to indicate GUI should be launched
            return None
        
        # Configuration listing
        if args.list_configs:
            # Create app without showing UI
            app = QApplication(sys.argv)
            keyboard_app = keyboard_app_class()
            
            configs = keyboard_app.config_manager.get_config_list()
            print("Available configurations:")
            for config in configs:
                print(f"  - {config}")
            return
        
        # Load specific config
        if args.load_config:
            app = QApplication(sys.argv)
            keyboard_app = keyboard_app_class()
            
            if not keyboard_app.keyboard.connected:
                if not keyboard_app.keyboard.connect():
                    logger.error("Failed to connect to keyboard")
                    return False
            
            keyboard_app.load_config(args.load_config)
            keyboard_app.send_config()
            logger.info(f"Loaded and applied configuration: {args.load_config}")
            keyboard_app.keyboard.disconnect()
            return
        
        # Effect application
        if args.effect:
            app = QApplication(sys.argv)
            keyboard_app = keyboard_app_class()
            
            if not keyboard_app.keyboard.connected:
                if not keyboard_app.keyboard.connect():
                    logger.error("Failed to connect to keyboard")
                    return False
            
            try:
                # Parse color if provided
                effect_color = None
                if args.effect_color:
                    if ',' in args.effect_color:
                        try:
                            r, g, b = map(int, args.effect_color.split(','))
                            effect_color = (r, g, b)
                        except:
                            pass
                    else:
                        # Handle named colors
                        color_map = {
                            "white": (255, 255, 255),
                            "red": (255, 0, 0),
                            "green": (0, 255, 0),
                            "blue": (0, 0, 255),
                            "yellow": (255, 255, 0),
                            "cyan": (0, 255, 255),
                            "magenta": (255, 0, 255),
                            "orange": (255, 165, 0),
                            "purple": (128, 0, 128)
                        }
                        effect_color = color_map.get(args.effect_color.lower(), (255, 255, 255))
                
                speed = args.effect_speed if hasattr(args, 'effect_speed') else 0.1
                
                if args.effect == 'rainbow':
                    keyboard_app.effects.set_rainbow_colors()
                elif args.effect == 'wave':
                    keyboard_app.effects.set_wave_effect(speed=speed)
                elif args.effect == 'function':
                    keyboard_app.effects.set_function_key_colors(effect_color or (255, 0, 0))
                elif args.effect == 'breathe':
                    keyboard_app.effects.breathe_effect(color=effect_color, speed=speed)
                elif args.effect == 'ripple':
                    keyboard_app.effects.ripple_effect(color=effect_color, speed=speed)
                elif args.effect == 'gradient':
                    keyboard_app.effects.gradient_effect(speed=speed)
                elif args.effect == 'reactive':
                    keyboard_app.effects.reactive_effect(highlight_color=effect_color)
                elif args.effect == 'spectrum':
                    keyboard_app.effects.spectrum_effect(speed=speed)
                elif args.effect == 'starlight':
                    keyboard_app.effects.starlight_effect(star_color=effect_color, density=0.1)
                
                # Wait for timeout or indefinitely
                if args.timeout:
                    logger.info(f"Effect applied. Waiting {args.timeout} seconds...")
                    time.sleep(args.timeout)
                else:
                    logger.info("Effect applied. Press Ctrl+C to exit.")
                    try:
                        while True:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        logger.info("Keyboard interrupt received, exiting")
            finally:
                # Restore default and disconnect
                keyboard_app.load_config()
                keyboard_app.send_config()
                keyboard_app.keyboard.disconnect()
            return
        
        # Text display mode
        if args.text:
            # Parse color if provided
            color = None
            if args.color:
                if ',' in args.color:
                    try:
                        r, g, b = map(int, args.color.split(','))
                        color = (r, g, b)
                    except:
                        color = args.color  # Use as color name
                else:
                    color = args.color  # Use as color name
            
            result = CommandLineInterface.display_text_on_keyboard(
                keyboard_app_class,
                args.text, 
                timeout=args.timeout, 
                color=color, 
                scroll=args.scroll,
                speed=args.speed
            )
            # Make sure to return a non-None value
            return result
        
        # If no command line action was taken, print help
        parser = argparse.ArgumentParser(description="Keyboard LED Configuration")
        parser.print_help()
        sys.exit(0) 