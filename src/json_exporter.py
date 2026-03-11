import json
import datetime
from pathlib import Path
from src.utils import setup_logger

logger = setup_logger(__name__)

def save_json_data(data: dict | list, output_dir: Path, identifier: str, start_date: str, end_date: str) -> Path:
    """
    Saves the given data to a JSON file.
    
    Args:
        data: The data to save.
        output_dir: The directory to save the file in.
        identifier: The endpoint identifier (used in filename).
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).
    
    Returns:
        The path to the saved file.
    """
    # Parse dates from YYYY-MM-DD to datetime objects
    try:
        dt_start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        dt_end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        
        # Format to DD-MM-YYYY for filename
        fmt_start = dt_start.strftime("%d-%m-%Y")
        fmt_end = dt_end.strftime("%d-%m-%Y")
        
    except ValueError:
        # Fallback if dates are not in expected format, just use as is but sanitize
        logger.warning(f"Date format mismatch. Using raw strings: {start_date}, {end_date}")
        fmt_start = start_date.replace('/', '-')
        fmt_end = end_date.replace('/', '-')

    filename = f"{identifier}_{fmt_start}_{fmt_end}.json"
    file_path = output_dir / filename
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"Saved JSON for {identifier} at {file_path}")
        return file_path
    
    except Exception as e:
        logger.error(f"Failed to save JSON for {identifier}: {e}")
        raise
