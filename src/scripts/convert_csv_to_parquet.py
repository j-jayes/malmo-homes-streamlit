"""
Convert CSV files to Parquet format.
"""

import pandas as pd
import argparse
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def convert_csv_to_parquet(input_path: Path, delete_csv: bool = False):
    """Convert a single CSV file to Parquet."""
    try:
        # Read CSV
        df = pd.read_csv(input_path)
        
        # Define output path
        output_path = input_path.with_suffix('.parquet')
        
        # Save to Parquet
        df.to_parquet(output_path, index=False)
        logger.info(f"✓ Converted {input_path} to {output_path}")
        
        if delete_csv:
            input_path.unlink()
            logger.info(f"Deleted {input_path}")
            
    except Exception as e:
        logger.error(f"Error converting {input_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Convert CSV files to Parquet")
    parser.add_argument("input_dir", type=Path, help="Directory to scan for CSV files")
    parser.add_argument("--recursive", "-r", action="store_true", help="Scan recursively")
    parser.add_argument("--delete", "-d", action="store_true", help="Delete original CSV files after conversion")
    
    args = parser.parse_args()
    
    if not args.input_dir.exists():
        logger.error(f"Input directory {args.input_dir} does not exist")
        return
    
    pattern = "**/*.csv" if args.recursive else "*.csv"
    csv_files = list(args.input_dir.glob(pattern))
    
    if not csv_files:
        logger.warning(f"No CSV files found in {args.input_dir}")
        return
    
    logger.info(f"Found {len(csv_files)} CSV files to convert")
    
    for csv_file in csv_files:
        convert_csv_to_parquet(csv_file, delete_csv=args.delete)

if __name__ == "__main__":
    main()
