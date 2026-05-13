import os
import json
import datetime
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv
from src.utils import setup_logger, get_project_root, ensure_directories, get_date_range
from src.config_loader import ensure_config_file
from src.api_client import APIClient
from src.json_exporter import save_json_data
from src.excel_converter import convert_json_to_excel

# Setup logger
logger = setup_logger()

def load_config(config_path: Path) -> dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_arguments(args_list=None):
    parser = argparse.ArgumentParser(description="RPA Report Generator")
    parser.add_argument(
        "--date", 
        type=str, 
        help="Reference date in YYYY-MM-DD format to simulate execution date. Defaults to today.",
        default=None
    )
    return parser.parse_args(args_list)

def main(args_list=None):
    args = parse_arguments(args_list)
    logger.info("Starting RPA Report Generator...")
    
    # Load environment variables
    load_dotenv()
    
    # Paths
    root_dir = get_project_root()
    config_path = root_dir / "config" / "endpoints.json"
    endpoints_source = root_dir / "Modelos_EndPoits-BFF.txt"
    output_base = root_dir / "SaidaRPA"
    json_dir = output_base / "Json"
    excel_dir = output_base / "Excel"
    
    # Ensure directories exist
    ensure_directories([json_dir, excel_dir])
    
    if not ensure_config_file(config_path, endpoints_source):
        logger.error(f"Config file not found at {config_path}. Please run setup or check paths.")
        return

    config = load_config(config_path)
    endpoints = config.get("endpoints", [])
    date_filter_mode = config.get("date_filter_mode", "monthly")
    
    logger.info(f"Date Filter Mode: {date_filter_mode}")
    
    if not endpoints:
        logger.warning("No endpoints found in configuration.")
        return

    # Determine Date Range
    reference_date_str = args.date
    reference_date = None
    if reference_date_str:
        try:
            reference_date = datetime.datetime.strptime(reference_date_str, "%Y-%m-%d").date()
            logger.info(f"Using provided reference date: {reference_date}")
        except ValueError:
            logger.error("Invalid date format. Please use YYYY-MM-DD.")
            return
    else:
        logger.info("Using current date as reference.")

    if date_filter_mode == 'custom':
        custom_start = config.get("custom_start_date")
        custom_end = config.get("custom_end_date")

        if not custom_start or not custom_end:
            logger.error("Custom mode requires 'custom_start_date' and 'custom_end_date' in config.")
            return

        try:
            # Validate format and range
            dt_start = datetime.datetime.strptime(custom_start, "%Y-%m-%d").date()
            dt_end = datetime.datetime.strptime(custom_end, "%Y-%m-%d").date()

            if dt_start > dt_end:
                logger.error(f"Invalid custom date range: Start ({dt_start}) cannot be after End ({dt_end}).")
                return
            
            start_date = custom_start
            end_date = custom_end
            
        except ValueError:
            logger.error("Invalid date format in config. Please use YYYY-MM-DD for custom dates.")
            return
    else:
        start_date, end_date = get_date_range(mode=date_filter_mode, reference_date=reference_date)
    
    logger.info(f"Calculated Date Range ({date_filter_mode}): Start={start_date}, End={end_date}")

    # Prepare Params
    # The API expects dtStart and dtEnd. 
    # Logic: Append these to any existing params. Requests library handles this via 'params' arg.
    query_params = {
        "dtStart": start_date,
        "dtEnd": end_date
    }

    client = APIClient()
    
    # Tracking results
    success_count = 0
    fail_count = 0
    
    for ep in endpoints:
        identifier = ep.get("identifier")
        url = ep.get("url")
        
        if not url:
            logger.warning(f"Skipping endpoint with no URL: {ep}")
            continue
            
        logger.info(f"Processing endpoint: {identifier}")
        
        # 1. Fetch Data with dynamic params
        # Note: If the base URL in config already has params, requests merges them.
        # But we cleaned the config to not have date params.
        data = client.fetch_data(url, params=query_params)
        
        if data:
            # 2. Save JSON
            # Pass start_date and end_date for filename generation (DD-MM-YYYY)
            
            try:
                json_path = save_json_data(
                    data=data, 
                    output_dir=json_dir, 
                    identifier=identifier, 
                    start_date=start_date, 
                    end_date=end_date
                )
                
                # 3. Convert to Excel
                excel_path = convert_json_to_excel(json_path, excel_dir)
                
                if excel_path:
                    success_count += 1
                else:
                    logger.warning(f"Excel conversion failed for {identifier}")
                    
            except Exception as e:
                logger.error(f"Error processing data for {identifier}: {e}")
                fail_count += 1
        else:
            logger.error(f"Failed to fetch data for {identifier}")
            fail_count += 1
        
        # Add delay to avoid rate limiting
        logger.info("Waiting 5 seconds before next request...")
        time.sleep(5)
            
    logger.info(f"Execution finished. Success: {success_count}, Failures: {fail_count}")

if __name__ == "__main__":
    main()
