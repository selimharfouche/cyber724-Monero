#!/usr/bin/env python3
"""
Parse a list of Monero nodes (like the one from paste.txt) and create a structured JSON file.
"""
import json
import re
import os
from urllib.parse import urlparse
from pathlib import Path

def is_onion_or_i2p(url):
    """Check if URL is a darknet URL (.onion or .i2p)"""
    parsed = urlparse(url)
    return parsed.netloc.endswith('.onion') or parsed.netloc.endswith('.i2p')

def parse_node_list(input_file):
    """Parse the node list from the provided file and create a JSON structure"""
    nodes = []
    
    try:
        with open(input_file, 'r') as f:
            lines = f.readlines()
        
        # Skip header line if present
        if "Type" in lines[0] and "URL" in lines[0]:
            lines = lines[1:]
        
        for line in lines:
            # Skip empty lines
            line = line.strip()
            if not line:
                continue
            
            # Split the line by tabs (or multiple spaces as fallback)
            parts = re.split(r'\t+|\s{2,}', line)
            
            # Extract data
            url = parts[1].strip() if len(parts) > 1 else None
            height = int(parts[2]) if len(parts) > 2 and parts[2].strip().isdigit() else None
            network = parts[4].strip() if len(parts) > 4 else "mainnet"
            last_checked = parts[5].strip() if len(parts) > 5 else None
            
            # Skip invalid entries
            if not url:
                continue
            
            # Determine node type (clearnet or darknet)
            node_type = "darknet" if is_onion_or_i2p(url) else "clearnet"
            
            # Create node object
            node = {
                "url": url,
                "type": node_type,
                "height": height,
                "network": network,
                "last_checked": last_checked
            }
            
            nodes.append(node)
        
        return nodes
    
    except Exception as e:
        print(f"Error parsing node list: {e}")
        return []

def main():
    # Get the script directory
    script_dir = Path(__file__).parent.absolute()
    
    # Define input and output paths
    input_file = os.path.join(script_dir, "paste.txt")
    output_dir = os.path.join(script_dir, "config")
    output_file = os.path.join(output_dir, "nodes.json")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Parse nodes
    nodes = parse_node_list(input_file)
    
    if not nodes:
        print("No nodes were found or parsed. Please check the input file.")
        return
    
    # Create JSON structure
    nodes_data = {
        "nodes": nodes,
        "total_count": len(nodes)
    }
    
    # Save to JSON file
    with open(output_file, 'w') as f:
        json.dump(nodes_data, f, indent=2)
    
    print(f"Successfully parsed {len(nodes)} nodes and saved to {output_file}")
    
    # Count node types for information
    clearnet_count = sum(1 for node in nodes if node["type"] == "clearnet")
    darknet_count = sum(1 for node in nodes if node["type"] == "darknet")
    
    print(f"Node types: {clearnet_count} clearnet, {darknet_count} darknet")

if __name__ == "__main__":
    main()
