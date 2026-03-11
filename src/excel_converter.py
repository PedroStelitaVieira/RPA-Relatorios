import json
import pandas as pd
from pathlib import Path
from src.utils import setup_logger

logger = setup_logger(__name__)

def convert_json_to_excel(json_path: Path, output_dir: Path) -> Path:
    """
    Converts a JSON file to an Excel file.
    
    Args:
        json_path: Path to the source JSON file.
        output_dir: Directory where the Excel file should be saved.
        
    Returns:
        Path to the saved Excel file.
    """
    try:
        # Load JSON data
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not data:
            logger.warning(f"JSON file {json_path} is empty. Skipping conversion.")
            return None

        # Normalize data (flatten hierarchical JSON)
        # If it's a list, we normalize it directly.
        # If it's a dict, we might need to decide how to normalize.
        # For this specific use case, the models show list of objects.
        if isinstance(data, list):
            df = pd.json_normalize(data)
        elif isinstance(data, dict):
             # Try to find list under common keys if nested, or just normalize the dict
            df = pd.json_normalize(data)
        else:
            logger.error(f"Unsupported JSON structure in {json_path}")
            return None
            
        # Create output filename (same basename as json but .xlsx)
        excel_filename = json_path.stem + ".xlsx"
        excel_path = output_dir / excel_filename
        
        # Save to Excel
        df.to_excel(excel_path, index=False)
        logger.info(f"Converted {json_path.name} to Excel at {excel_path}")
        
        return excel_path

    except Exception as e:
        logger.error(f"Failed to convert {json_path} to Excel: {e}")
        return None
