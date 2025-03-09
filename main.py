#!/usr/bin/env python3
"""
Monero Node Tracker - Main Script

This script monitors Monero nodes, tracks their status, and
sends alerts via Telegram.
"""
import os
import argparse
import datetime
import time
from pathlib import Path
import logging
from urllib.parse import urlparse

from utils.logging_utils import setup_logger
from utils.tor_utils import ensure_tor_running, get_tor_session
from utils.file_utils import load_json, save_json
from telegram_bot import send_scan_results

# Set up logging
logger = setup_logger()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

# Default settings if config file doesn't exist
DEFAULT_SETTINGS = {
    "scan_interval_minutes": 60,
    "telegram": {
        "enabled": True
    },
    "tor": {
        "enabled": True,
        "control_port": 9051,
        "socks_port": 9050
    }
}

def is_darknet_url(url):
    """Check if URL is a darknet URL (.onion or .i2p)"""
    parsed = urlparse(url)
    return parsed.netloc.endswith('.onion') or parsed.netloc.endswith('.i2p')

def load_settings():
    """Load settings from config file or create default"""
    settings_path = os.path.join(CONFIG_DIR, "settings.json")
    
    if os.path.exists(settings_path):
        settings = load_json(settings_path)
        logger.info("Settings loaded from config file")
    else:
        settings = DEFAULT_SETTINGS
        save_json(settings, settings_path)
        logger.info("Default settings created in config file")
    
    return settings

def load_nodes():
    """Load node list from the config file"""
    nodes_path = os.path.join(CONFIG_DIR, "nodes.json")
    
    if not os.path.exists(nodes_path):
        logger.error(f"Nodes file not found: {nodes_path}")
        return []
    
    nodes_data = load_json(nodes_path)
    if not nodes_data or "nodes" not in nodes_data:
        logger.error("Invalid nodes data format")
        return []
    
    return nodes_data["nodes"]

def check_node(node, use_tor=True):
    """Check a single Monero node's status with multiple verification methods"""
    import requests
    
    url = node["url"]
    node_type = node["type"]
    
    # Create appropriate session based on URL type
    if node_type == "darknet" and use_tor:
        session = get_tor_session()
    else:
        session = requests
    
    # Remove trailing slash if present
    base_url = url.rstrip('/')
    
    # Define methods that are most likely to return height information
    height_methods = [
        # Method 1: Direct get_info endpoint - most likely to have height
        {"type": "rpc", "url": f"{base_url}/get_info", "data": {"jsonrpc": "2.0", "id": "0", "method": "get_info"}},
        # Method 2: Standard RPC check for get_info
        {"type": "rpc", "url": f"{base_url}/json_rpc", "data": {"jsonrpc": "2.0", "id": "0", "method": "get_info"}},
        # Method 3: Get last block header (has height in header)
        {"type": "rpc", "url": f"{base_url}/json_rpc", "data": {"jsonrpc": "2.0", "id": "0", "method": "get_last_block_header"}}
    ]
    
    # Try height-specific methods first
    for method in height_methods:
        try:
            response = session.post(method["url"], json=method["data"], timeout=15)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'result' in data:
                        result = data['result']
                        # Different methods return height in different locations
                        height = None
                        
                        # Direct get_info has height directly
                        if 'height' in result:
                            height = result['height']
                        # get_last_block_header has height in block_header
                        elif 'block_header' in result and 'height' in result['block_header']:
                            height = result['block_header']['height']
                        
                        if height is not None:
                            return {
                                "url": url,
                                "type": node_type,
                                "status": "online",
                                "height": height,
                                "version": result.get('version', ''),
                                "difficulty": result.get('difficulty', 0)
                            }
                except Exception:
                    # JSON parsing failed, try next method
                    continue
        except Exception:
            # Request failed, try next method
            continue
    
    # Fallback methods just to check if node is online
    basic_methods = [
        {"type": "get", "url": base_url},
        {"type": "get", "url": f"{base_url}/get_info"}
    ]
    
    # If height methods failed, try basic methods to at least determine if node is online
    for method in basic_methods:
        try:
            response = session.get(method["url"], timeout=15)
            
            # Any response means the node exists
            if response.status_code < 500:
                return {
                    "url": url,
                    "type": node_type,
                    "status": "online",
                    "note": f"Responded with status {response.status_code}",
                    "height": 0  # No height information available
                }
        except Exception:
            continue
    
    # All methods failed, node is offline
    return {
        "url": url,
        "type": node_type,
        "status": "offline",
        "error": "Failed all connection methods",
        "height": 0
    }
def main():
    """Main function to run the Monero node tracker"""
    parser = argparse.ArgumentParser(description="Monero Node Tracker")
    parser.add_argument("--continuous", action="store_true", help="Run in continuous mode")
    parser.add_argument("--no-telegram", action="store_true", help="Disable Telegram notifications")
    parser.add_argument("--no-tor", action="store_true", help="Disable Tor for darknet URLs")
    args = parser.parse_args()
    
    # Load settings
    settings = load_settings()
    
    # Disable Telegram if specified
    if args.no_telegram:
        settings["telegram"]["enabled"] = False
    
    # Ensure Tor is running if enabled
    use_tor = settings["tor"]["enabled"] and not args.no_tor
    if use_tor:
        if not ensure_tor_running(settings["tor"]["socks_port"]):
            logger.error("Failed to connect to Tor. Darknet nodes might be unreachable.")
            if input("Continue without Tor? (y/n): ").lower() != 'y':
                return
            use_tor = False
    
    # Run a single scan or continuous monitoring
    try:
        if args.continuous:
            logger.info(f"Starting continuous monitoring every {settings['scan_interval_minutes']} minutes")
            while True:
                run_scan(settings, use_tor)
                logger.info(f"Next scan in {settings['scan_interval_minutes']} minutes")
                time.sleep(settings['scan_interval_minutes'] * 60)
        else:
            # Default to single scan
            logger.info("Running single scan mode")
            run_scan(settings, use_tor)
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Error in main function: {e}")
def run_scan(settings, use_tor=True):
    """Run a single scan of all Monero nodes"""
    logger.info("Starting Monero node scan")
    
    # Load nodes
    nodes = load_nodes()
    if not nodes:
        logger.error("No nodes to scan")
        return False
    
    # Get current timestamp
    timestamp = datetime.datetime.now().isoformat()
    
    # Scan nodes
    results = []
    online_count = 0
    
    logger.info(f"Scanning {len(nodes)} nodes...")
    for i, node in enumerate(nodes):
        logger.info(f"[{i+1}/{len(nodes)}] Checking {node['url']}...")
        result = check_node(node, use_tor)
        
        # Print node status directly to console
        status_msg = f"Node {node['url']} is {result['status'].upper()}"
        if result['status'] == 'online':
            online_count += 1
            height = result.get('height', 'unknown')
            status_msg += f" (height: {height})"
            print(status_msg)
        else:
            print(status_msg)
            
        results.append(result)
    
    # Add timestamp to data
    scan_result = {
        "timestamp": timestamp,
        "nodes": results
    }
    
    # Save to JSON file
    history_file = os.path.join(DATA_DIR, "node_history.json")
    current_history = load_json(history_file) or {"scans": []}
    current_history["scans"].append(scan_result)
    
    # Limit history to last 10 scans to avoid huge files
    if len(current_history["scans"]) > 10:
        current_history["scans"] = current_history["scans"][-10:]
    
    save_json(current_history, history_file)
    
    # Also save most recent scan to a separate file
    latest_file = os.path.join(DATA_DIR, "latest_scan.json")
    save_json(scan_result, latest_file)
    
    # Count node statuses
    total = len(results)
    offline = sum(1 for node in results if node["status"] == "offline")
    error = sum(1 for node in results if node["status"] != "online" and node["status"] != "offline")
    
    logger.info(f"Scan completed: {online_count} online, {offline} offline, {error} error, out of {total} total nodes")
    
    # Send Telegram notification if enabled
    if settings["telegram"]["enabled"]:
        # Check if environment variables exist
        if not os.environ.get("TELEGRAM_BOT_TOKEN") or not os.environ.get("TELEGRAM_CHANNEL_ID"):
            logger.warning("Telegram environment variables not set. Skipping notification.")
        else:
            send_scan_results(scan_result)
    
    return scan_result

if __name__ == "__main__":
    main()