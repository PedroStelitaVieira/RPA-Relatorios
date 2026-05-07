import logging
import datetime
import os
from pathlib import Path

def setup_logger(name=__name__, log_file='execution.log', level=logging.INFO):
    """Function to setup as many loggers as you want"""
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    
    # Ensure log file is created in the project root
    log_path = get_project_root() / log_file
    
    handler = logging.FileHandler(str(log_path))        
    handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding handlers multiple times
    if not logger.handlers:
        logger.addHandler(handler)
        logger.addHandler(console_handler)
        
    return logger

import sys

def get_project_root() -> Path:
    """Returns the project root directory."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent

def ensure_directories(paths: list[Path]):
    """Ensures that the specified directories exist."""
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)

def get_date_range(mode: str = 'monthly', reference_date: datetime.date = None) -> tuple[str, str]:
    """
    Calculates the start and end dates based on the mode and reference_date.
    
    Args:
        mode: 'monthly' (previous month) or 'weekly' (last 7 days). Defaults to 'monthly'.
        reference_date: The date to calculate relative to. Defaults to today.
        
    Returns:
        A tuple containing (start_date_str, end_date_str) in 'YYYY-MM-DD' format.
    """
    if reference_date is None:
        reference_date = datetime.date.today()
        
    if mode == 'weekly':
        # Weekly: D-7 to D (End date is reference_date, Start is 7 days prior)
        # Requirement: dtStart = current date - 7 days (D-7), dtEnd = current date (D)
        end_date = reference_date
        start_date = reference_date - datetime.timedelta(days=7)
        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
        
    else: # Default to 'monthly'
        # Monthly: First and last day of the previous month
        # First day of partial month is always 1
        # To get previous month, we replace day with 1 and subtract 1 day
        first_day_current_month = reference_date.replace(day=1)
        last_day_previous_month = first_day_current_month - datetime.timedelta(days=1)
        first_day_previous_month = last_day_previous_month.replace(day=1)
        
        return first_day_previous_month.strftime("%Y-%m-%d"), last_day_previous_month.strftime("%Y-%m-%d")
