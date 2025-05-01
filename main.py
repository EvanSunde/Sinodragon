import sys
import logging
from PyQt5.QtWidgets import QApplication
from keyboard_layout import KeyboardConfigApp

# Configure logging with INFO level instead of DEBUG
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='keyboard_app.log',  # Also save to file
    filemode='a'  # Append to existing log
)

# Add console handler to show logs in console as well
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    # Create the Qt Application
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show the keyboard config application
    keyboard_app = KeyboardConfigApp()
    keyboard_app.show()
    
    # Start the application event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    logger.info("Starting Keyboard LED Configuration Application")
    main()
    logger.info("Application GUI initialized and shown") 