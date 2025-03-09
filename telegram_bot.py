"""
Telegram bot integration for the Monero Node Tracker
"""
import logging
import requests
import os
from datetime import datetime

# Set up logger
logger = logging.getLogger(__name__)

def send_telegram_message(message):
    """Send a message via Telegram bot API using environment variables"""
    try:
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHANNEL_ID")
        
        if not token or not chat_id:
            logger.error("Telegram token or channel ID not found in environment variables")
            return False
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            logger.info("Telegram message sent successfully to channel")
            return True
        else:
            logger.error(f"Failed to send Telegram message: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False

def format_scan_results(scan_result, scan_time=None):
    """Format scan results for Telegram message"""
    # Parse timestamp
    try:
        timestamp = datetime.fromisoformat(scan_result["timestamp"])
        formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        formatted_time = scan_result["timestamp"]
    
    # Count node statuses
    nodes = scan_result["nodes"]
    total_nodes = len(nodes)
    online_nodes = sum(1 for node in nodes if node["status"] == "online")
    clearnet_online = sum(1 for node in nodes if node["type"] == "clearnet" and node["status"] == "online")
    darknet_online = sum(1 for node in nodes if node["type"] == "darknet" and node["status"] == "online")
    
    # Calculate network statistics
    online_with_height = [node for node in nodes if node["status"] == "online" and node.get("height", 0) > 0]
    heights = [node.get("height", 0) for node in online_with_height]
    max_height = max(heights) if heights else 0
    
    # Find median height to detect potential chain splits
    if heights:
        sorted_heights = sorted(heights)
        mid = len(sorted_heights) // 2
        if len(sorted_heights) % 2 == 0:
            median_height = (sorted_heights[mid-1] + sorted_heights[mid]) / 2
        else:
            median_height = sorted_heights[mid]
    else:
        median_height = 0
    
    # Count nodes near the highest height (within 10 blocks)
    synced_nodes = sum(1 for h in heights if max_height - h <= 10)
    synced_percent = (synced_nodes / len(online_with_height) * 100) if online_with_height else 0
    
    # Calculate network health score (0-100)
    if total_nodes > 0 and online_with_height:
        health_score = (online_nodes / total_nodes * 0.5 + synced_nodes / len(online_with_height) * 0.5) * 100
    else:
        health_score = 0
    
    # Create message
    message = f"*Monero Node Scan Results*\n"
    message += f"📅 *Time*: {formatted_time}\n"
    
    # Include scan time if provided
    if scan_time:
        message += f"⏱️ *Scan Duration*: {scan_time:.1f} seconds\n"
    
    message += f"📊 *Summary*:\n"
    message += f"- Total nodes: {total_nodes}\n"
    message += f"- Online: {online_nodes}/{total_nodes} ({online_nodes/total_nodes*100:.1f}%)\n"
    message += f"- Clearnet: {clearnet_online} | Darknet: {darknet_online}\n\n"
    
    # Network health indicators
    message += f"*Network Status*:\n"
    message += f"- Block Height: {max_height}\n"
    message += f"- Synced Nodes: {synced_nodes}/{len(online_with_height)} ({synced_percent:.1f}%)\n"
    message += f"- Health Score: {health_score:.1f}/100\n"
    
    return message

def send_scan_results(scan_result, scan_time=None):
    """Send formatted scan results via Telegram"""
    message = format_scan_results(scan_result, scan_time)
    return send_telegram_message(message)