"""
Tor utility functions for the Monero Node Tracker
"""
import socket
import subprocess
import time
import logging
import requests
import os

# Set up logger
logger = logging.getLogger(__name__)

def get_tor_session():
    """Create a requests session that routes through Tor"""
    try:
        # Make sure PySocks is installed properly
        import socks
        # Removed the "PySocks is installed" log message
    except ImportError:
        logger.error("PySocks is not properly installed. Run: pip install -U requests[socks] PySocks")
        # Try to continue anyway
    
    session = requests.session()
    # Tor uses port 9050 by default
    session.proxies = {
        'http': 'socks5h://127.0.0.1:9050',
        'https': 'socks5h://127.0.0.1:9050'
    }
    return session


def is_tor_running(port=9050):
    """Check if Tor is already running on the specified port"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(('127.0.0.1', port))
        s.close()
        
        if result == 0:
            logger.info(f"Tor port {port} is open and accepting connections")
            return True
        else:
            logger.warning(f"Tor port {port} is not open (result code: {result})")
            return False
    except Exception as e:
        logger.error(f"Error checking if Tor is running: {e}")
        return False

def start_tor():
    """Start Tor as a subprocess"""
    try:
        # Check if Tor is already running
        if is_tor_running():
            logger.info("Tor is already running")
            return True
            
        # Check if Tor is installed
        tor_path = subprocess.run(
            ["which", "tor"], 
            capture_output=True, 
            text=True
        ).stdout.strip()
        
        if not tor_path:
            logger.error("Tor is not installed. Please install Tor.")
            return False
        
        logger.info("Starting Tor...")
        # Start Tor as a background process
        subprocess.Popen(
            ["tor"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for Tor to start
        for i in range(30):
            if is_tor_running():
                logger.info("Tor started successfully")
                return True
            logger.info(f"Waiting for Tor to start (attempt {i+1}/30)...")
            time.sleep(1)
        
        logger.error("Tor failed to start within the timeout period")
        return False
    except Exception as e:
        logger.error(f"Error starting Tor: {e}")
        return False

def ensure_tor_running(port=9050):
    """Ensure Tor is running, start it if necessary"""
    # Check if we're running in GitHub Actions
    in_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
    
    if in_github_actions:
        logger.info("Running in GitHub Actions environment. Checking if Tor is available...")
        if is_tor_running(port):
            return True
        else:
            logger.error("Tor does not appear to be running in GitHub Actions environment")
            return False
    
    # Normal flow for local environment
    if is_tor_running(port):
        # Test Tor by making a brief request
        try:
            session = get_tor_session()
            session.get("https://check.torproject.org", timeout=5)
            logger.info("Tor is working properly")
        except Exception as e:
            logger.warning(f"Tor is running but may not be working correctly: {e}")
        
        return True
    
    return start_tor()

def test_tor_connection():
    """Test if Tor connection is working by accessing check.torproject.org"""
    try:
        logger.info("Testing Tor connection...")
        session = get_tor_session()
        response = session.get('https://check.torproject.org/', timeout=10)
        
        if 'Congratulations' in response.text:
            logger.info("Successfully connected to Tor!")
            return True
        else:
            logger.warning("Connected to check.torproject.org, but Tor is not being used")
            return False
    except Exception as e:
        logger.error(f"Failed to connect to Tor: {e}")
        return False