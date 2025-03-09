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

def format_scan_results(scan_result):
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
    
    # Find highest block height
    heights = [node.get("height", 0) for node in nodes if node.get("status") == "online" and node.get("height", 0) > 0]
    max_height = max(heights) if heights else 0
    
    # Create message
    message = f"*Monero Node Scan Results*\n"
    message += f"📅 *Time*: {formatted_time}\n"
    message += f"📊 *Summary*:\n"
    message += f"- Total nodes: {total_nodes}\n"
    message += f"- Online nodes: {online_nodes}/{total_nodes} ({online_nodes/total_nodes*100:.1f}%)\n"
    message += f"- Clearnet online: {clearnet_online}\n"
    message += f"- Darknet online: {darknet_online}\n"
    message += f"- Highest block: {max_height}\n\n"
    
    # Add details for online nodes with highest blocks
    message += f"*Top Online Nodes*:\n"
    
    # Get top 5 nodes by height
    top_nodes = sorted([node for node in nodes if node["status"] == "online" and node.get("height", 0) > 0], 
                       key=lambda x: x.get("height", 0), reverse=True)[:5]
    
    for i, node in enumerate(top_nodes):
        url_display = node["url"].split("://")[1].split(":")[0]
        # Truncate long .onion addresses
        if len(url_display) > 30:
            url_display = url_display[:20] + "..." + url_display[-7:]
        
        height = node.get("height", "N/A")
        message += f"{i+1}. `{url_display}` - Height: {height}\n"
    
    return message

def send_scan_results(scan_result, telegram_config=None):
    """Send formatted scan results via Telegram"""
    message = format_scan_results(scan_result)
    return send_telegram_message(message)