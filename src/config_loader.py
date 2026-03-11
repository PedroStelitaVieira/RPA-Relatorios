import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs

def parse_endpoints_file(input_file: Path, output_file: Path):
    """Reads the raw endpoints text file and creates a structured JSON config."""
    endpoints = []
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            url = line.strip()
            if not url:
                continue
            
            parsed = urlparse(url)
            path_segments = parsed.path.split('/')
            # Use the last segment of the path as the identifier (e.g., 'status-distribuidora')
            identifier = path_segments[-1] if path_segments else 'unknown'
            
            # Extract basic query params for reference if needed
            # params = parse_qs(parsed.query)
            
            endpoints.append({
                "identifier": identifier,
                "url": url,
                "description": f"Endpoint for {identifier}"
            })
            
        # Write to JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "date_filter_mode": "monthly",
                "endpoints": endpoints
            }, f, indent=4)
            
        print(f"Successfully created config/endpoints.json with {len(endpoints)} endpoints.")
        
    except Exception as e:
        print(f"Error parsing endpoints file: {e}")

if __name__ == "__main__":
    # Define paths relative to this script execution or absolute
    base_dir = Path(__file__).parent.parent
    input_path = base_dir / "Modelos_EndPoits-BFF.txt"
    output_path = base_dir / "config" / "endpoints.json"
    
    # Ensure config dir exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    parse_endpoints_file(input_path, output_path)
