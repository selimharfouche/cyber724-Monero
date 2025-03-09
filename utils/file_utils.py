"""
File utility functions for the Monero Node Tracker
"""
import json
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

# Set up logger
logger = logging.getLogger(__name__)

def load_json(filepath):
    """Load JSON data from a file"""
    try:
        if not os.path.exists(filepath):
            logger.debug(f"File does not exist: {filepath}")
            return None
            
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in file: {filepath}")
        return None
    except Exception as e:
        logger.error(f"Error loading JSON from {filepath}: {e}")
        return None

def save_json(data, filepath):
    """Save JSON data to a file"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.debug(f"Data saved to {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error saving JSON to {filepath}: {e}")
        return False