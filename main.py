#! /usr/bin/python3
import sys
import argparse
from PyQt5.QtWidgets import QApplication

# Import utility functions
from utils import setup_logging

# Import from new structure
from ui.main_window import KeyboardConfigApp
from features.cli import CommandLineInterface

def main():
    """Main application entry point"""
    # Set up logging
    setup_logging(filename='keyboard_app.log')
    
    # Parse specific arguments for the main app
    parser = argparse.ArgumentParser(description="Keyboard LED Configuration")
    parser.add_argument('--background', '-b', action='store_true', help='Start application in background mode')
    parser.add_argument('--no-connect', action='store_true', help='Do not automatically connect to keyboard on startup')
    
    # Only parse known args to allow CLI module to handle its own args
    args, _ = parser.parse_known_args()
    
    # Handle command line interface
    result = CommandLineInterface.handle_command_line(KeyboardConfigApp)
    
    # If command line handling requested GUI launch (returns None), launch the GUI
    if result is None:
        # Normal GUI mode
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        # Create the keyboard app
        keyboard_app = KeyboardConfigApp()
        
        # Set auto-connect preference
        if args.no_connect:
            keyboard_app.auto_connect = False
        
        # Show window unless background mode is requested
        if not args.background:
            keyboard_app.show()
        
        sys.exit(app.exec_())
    
    # Add explicit exit for CLI operations
    else:
        sys.exit(0)  # Exit after CLI operations complete

if __name__ == "__main__":
    main() 