"""
Node scraper module for the Monero Node Tracker
Handles scraping node data from various sources
"""
import re
import json
import requests
import logging
from urllib.parse import urlparse

from utils.tor_utils import get_tor_session

# Set up logger
logger = logging.getLogger(__name__)

def is_darknet_url(url):
    """Check if URL is a darknet URL (.onion or .i2p)"""
    parsed = urlparse(url)
    return parsed.netloc.endswith('.onion') or parsed.netloc.endswith('.i2p')

def get_node_info(url):
    """Get info from a single Monero node"""
    try:
        parsed_url = urlparse(url)
        node_type = "darknet" if is_darknet_url(url) else "clearnet"
        
        # Create appropriate session (Tor for .onion/.i2p, regular for clearnet)
        if node_type == "darknet":
            session = get_tor_session()
        else:
            session = requests
        
        # Try to get node info via RPC
        rpc_url = f"{parsed_url.scheme}://{parsed_url.netloc}/get_info"
        
        # Set timeout to avoid hanging
        response = session.post(
            rpc_url, 
            json={"jsonrpc": "2.0", "id": "0", "method": "get_info"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract relevant Monero node data
            if 'result' in data:
                result = data['result']
                return {
                    "url": url,
                    "type": node_type,
                    "status": "online",
                    "height": result.get('height', 0),
                    "version": result.get('version', ''),
                    "top_block_hash": result.get('top_block_hash', ''),
                    "difficulty": result.get('difficulty', 0),
                    "tx_count": result.get('tx_count', 0),
                    "tx_pool_size": result.get('tx_pool_size', 0),
                    "alt_blocks_count": result.get('alt_blocks_count', 0),
                    "outgoing_connections_count": result.get('outgoing_connections_count', 0),
                    "incoming_connections_count": result.get('incoming_connections_count', 0),
                    "white_peerlist_size": result.get('white_peerlist_size', 0),
                    "grey_peerlist_size": result.get('grey_peerlist_size', 0),
                    "mainnet": result.get('mainnet', True),
                    "testnet": result.get('testnet', False),
                    "stagenet": result.get('stagenet', False),
                    "nettype": "mainnet" if result.get('mainnet', True) else 
                              "testnet" if result.get('testnet', False) else 
                              "stagenet" if result.get('stagenet', False) else "unknown"
                }
        
        # Fallback: Try to parse HTML for height information
        # This is a backup method for nodes that don't expose RPC
        try:
            response = session.get(url, timeout=10)
            if response.status_code == 200:
                # Look for height information in the HTML
                height_match = re.search(r'Height: (\d+)', response.text)
                if height_match:
                    height = int(height_match.group(1))
                    return {
                        "url": url,
                        "type": node_type,
                        "status": "online",
                        "height": height,
                        "source": "html_parse"
                    }
        except Exception as e:
            logger.debug(f"Failed to parse HTML from {url}: {e}")
        
        # If we got here but had a 200 response earlier, mark as online with limited info
        if response.status_code == 200:
            return {
                "url": url,
                "type": node_type,
                "status": "online_limited",
                "error": "Limited node data available"
            }
        
        return {
            "url": url,
            "type": node_type,
            "status": "error",
            "error": f"HTTP {response.status_code}"
        }
        
    except requests.exceptions.Timeout:
        logger.warning(f"Connection to {url} timed out")
        return {
            "url": url,
            "type": node_type if 'node_type' in locals() else "unknown",
            "status": "timeout",
            "error": "Connection timed out"
        }
    except requests.exceptions.ConnectionError:
        logger.warning(f"Failed to connect to {url}")
        return {
            "url": url,
            "type": node_type if 'node_type' in locals() else "unknown",
            "status": "offline",
            "error": "Connection failed"
        }
    except Exception as e:
        logger.error(f"Error fetching data from {url}: {e}")
        return {
            "url": url,
            "type": node_type if 'node_type' in locals() else "unknown",
            "status": "error",
            "error": str(e)
        }

def scrape_nodes(node_urls):
    """Scrape data from all provided Monero nodes"""
    results = []
    
    for url in node_urls:
        logger.info(f"Checking node: {url}")
        node_info = get_node_info(url)
        results.append(node_info)
    
    # Sort results by type and status
    results.sort(key=lambda x: (x["type"], x["status"] != "online", x.get("height", 0) * -1))
    
    return results
