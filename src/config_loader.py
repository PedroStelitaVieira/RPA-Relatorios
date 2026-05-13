import json
from pathlib import Path
from urllib.parse import urlparse

def build_default_config(input_file: Path, date_filter_mode: str = "monthly") -> dict:
    """Reads the raw endpoints text file and builds the default config payload."""
    endpoints = []

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        url = line.strip()
        if not url:
            continue

        parsed = urlparse(url)
        path_segments = parsed.path.split('/')
        identifier = path_segments[-1] if path_segments else 'unknown'

        endpoints.append({
            "identifier": identifier,
            "url": url,
            "description": f"Endpoint for {identifier}"
        })

    return {
        "date_filter_mode": date_filter_mode,
        "custom_start_date": None,
        "custom_end_date": None,
        "endpoints": endpoints
    }

def parse_endpoints_file(input_file: Path, output_file: Path, date_filter_mode: str = "monthly"):
    """Reads the raw endpoints text file and creates a structured JSON config."""
    try:
        config = build_default_config(input_file, date_filter_mode=date_filter_mode)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

        print(f"Successfully created config/endpoints.json with {len(config['endpoints'])} endpoints.")
    except Exception as e:
        print(f"Error parsing endpoints file: {e}")

def ensure_config_file(config_path: Path, endpoints_source: Path, date_filter_mode: str = "monthly") -> bool:
    """Creates config/endpoints.json on first use when it does not exist yet."""
    if config_path.exists():
        return True

    if not endpoints_source.exists():
        return False

    config_path.parent.mkdir(parents=True, exist_ok=True)
    parse_endpoints_file(endpoints_source, config_path, date_filter_mode=date_filter_mode)
    return config_path.exists()

if __name__ == "__main__":
    # Define paths relative to this script execution or absolute
    base_dir = Path(__file__).parent.parent
    input_path = base_dir / "Modelos_EndPoits-BFF.txt"
    output_path = base_dir / "config" / "endpoints.json"
    
    # Ensure config dir exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    parse_endpoints_file(input_path, output_path)
