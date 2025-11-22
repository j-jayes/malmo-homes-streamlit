"""
Batch processing manager for property scraping.
Handles reading URLs from CSV, scraping in batches, saving to Parquet files,
and tracking progress with resume capability.
"""

import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import pyarrow as pa
import pyarrow.parquet as pq

from src.scrapers.property_detail_scraper import PropertyScraper
from src.scrapers.progress_tracker import ProgressTracker
from src.models.property_schema import BaseProperty, SoldProperty, ForSaleProperty

logger = logging.getLogger(__name__)


class BatchManager:
    """Manages batch processing of property URLs with Parquet output."""
    
    def __init__(
        self,
        input_file: Path,
        output_dir: Path,
        batch_size: int = 100,
        headless: bool = True,
        progress_tracker: ProgressTracker | None = None,
    ):
        """
        Initialize batch manager.
        
        Args:
            input_file: Path to CSV file with URLs (must have 'url' column)
            output_dir: Directory to save Parquet files
            batch_size: Number of properties to process per batch
            headless: Whether to run browser in headless mode
        """
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        self.batch_size = batch_size
        self.headless = headless
        self.progress_tracker = progress_tracker
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Metadata tracking
        self.metadata_file = self.output_dir / "metadata.json"
        self.metadata = self._load_metadata()
        
        # Initialize scraper
        self.scraper = PropertyScraper(headless=headless)
        
    def _load_metadata(self) -> Dict:
        """Load processing metadata from file."""
        if self.metadata_file.exists():
            with open(self.metadata_file) as f:
                return json.load(f)
        
        return {
            "created_at": datetime.now().isoformat(),
            "batches": {},
            "total_processed": 0,
            "total_successful": 0,
            "total_failed": 0,
            "last_batch": 0
        }
    
    def _save_metadata(self):
        """Save processing metadata to file."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        if self.progress_tracker:
            self.progress_tracker.save()
    
    def _read_urls(self) -> List[Dict[str, str]]:
        """
        Read URLs from CSV file.
        
        Returns:
            List of dicts with at least 'url' key
        """
        urls = []
        skipped = 0
        with open(self.input_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'url' in row:
                    if self.progress_tracker and self.progress_tracker.should_skip(row):
                        skipped += 1
                        continue
                    urls.append(row)
                else:
                    logger.warning(f"Row missing 'url' column: {row}")
        
        logger.info(f"Loaded {len(urls)} URLs from {self.input_file}")
        if skipped:
            logger.info("Skipping %s URLs already present in progress cache", skipped)
        return urls
    
    def _property_to_dict(self, prop: BaseProperty) -> Dict:
        """Convert Pydantic model to dict for Parquet."""
        data = prop.model_dump()
        
        # Convert dates to strings (Parquet handles dates, but this is more compatible)
        for key, value in data.items():
            if hasattr(value, 'isoformat'):
                data[key] = value.isoformat()
        
        return data
    
    def _save_batch_to_parquet(self, batch_num: int, properties: List[BaseProperty]):
        """
        Save batch of properties to Parquet file.
        
        Args:
            batch_num: Batch number for filename
            properties: List of property models to save
        """
        if not properties:
            logger.warning(f"Batch {batch_num} has no properties to save")
            return
        
        # Convert to list of dicts
        records = [self._property_to_dict(prop) for prop in properties]
        
        # Create PyArrow table
        table = pa.Table.from_pylist(records)
        
        # Save to Parquet with compression
        output_file = self.output_dir / f"batch_{batch_num:04d}.parquet"
        pq.write_table(
            table,
            output_file,
            compression='snappy',  # Good balance of speed and compression
            use_dictionary=True,   # Compress repeated strings
        )
        
        file_size = output_file.stat().st_size / 1024  # KB
        logger.info(f"✓ Saved batch {batch_num}: {len(properties)} properties, {file_size:.1f}KB")
        
        # Update metadata
        self.metadata["batches"][str(batch_num)] = {
            "count": len(properties),
            "file_size_kb": round(file_size, 2),
            "timestamp": datetime.now().isoformat(),
            "file": str(output_file.name)
        }
    
    def process_batch(
        self,
        batch_num: int,
        urls: List[Dict[str, str]],
        save_failures: bool = True
    ) -> Dict:
        """
        Process a single batch of URLs.
        
        Args:
            batch_num: Batch number
            urls: List of URL records to process
            save_failures: Whether to save failed URLs to separate file
            
        Returns:
            Dict with processing statistics
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing batch {batch_num}: {len(urls)} properties")
        logger.info(f"{'='*60}")
        
        successful = []
        failed = []
        
        for i, record in enumerate(urls, 1):
            url = record['url']
            logger.info(f"[{i}/{len(urls)}] {url}")
            
            try:
                property_data = self.scraper.scrape_property(url)
                
                if property_data:
                    successful.append(property_data)
                    logger.info(f"  ✓ Success: {property_data.address}")
                    if self.progress_tracker:
                        self.progress_tracker.record_success(
                            property_id=property_data.property_id,
                            url=property_data.url,
                        )
                else:
                    failed.append({**record, 'error': 'No data returned'})
                    logger.error(f"  ✗ Failed: No data returned")
                    
            except Exception as e:
                failed.append({**record, 'error': str(e)})
                logger.error(f"  ✗ Failed: {e}")
        
        # Save successful properties to Parquet
        if successful:
            self._save_batch_to_parquet(batch_num, successful)
        
        # Save failed URLs to CSV for retry
        if failed and save_failures:
            failures_file = self.output_dir / f"batch_{batch_num:04d}_failures.csv"
            with open(failures_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['url', 'error'])
                writer.writeheader()
                writer.writerows(failed)
            logger.warning(f"Saved {len(failed)} failures to {failures_file}")
        
        # Update metadata
        stats = {
            "processed": len(urls),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(urls) * 100 if urls else 0
        }
        
        self.metadata["total_processed"] += stats["processed"]
        self.metadata["total_successful"] += stats["successful"]
        self.metadata["total_failed"] += stats["failed"]
        self.metadata["last_batch"] = batch_num
        self._save_metadata()
        
        logger.info(f"\nBatch {batch_num} complete: {stats['successful']}/{stats['processed']} successful ({stats['success_rate']:.1f}%)")
        return stats
    
    def process_all(
        self,
        batch_start: Optional[int] = None,
        batch_end: Optional[int] = None,
        resume: bool = True
    ) -> Dict:
        """
        Process all URLs in batches.
        
        Args:
            batch_start: Starting batch number (0-indexed), defaults to 0 or last batch if resume
            batch_end: Ending batch number (exclusive), defaults to all remaining
            resume: Whether to resume from last batch
            
        Returns:
            Dict with overall processing statistics
        """
        # Load URLs
        urls = self._read_urls()
        
        # Calculate batches
        total_batches = (len(urls) + self.batch_size - 1) // self.batch_size
        
        # Determine start batch
        if resume and batch_start is None:
            last_batch = self.metadata.get("last_batch", -1)
            batch_start = last_batch + 1 if last_batch >= 0 else 0
        elif batch_start is None:
            batch_start = 0
        
        # Determine end batch
        if batch_end is None:
            batch_end = total_batches
        
        logger.info(f"\n{'='*60}")
        logger.info(f"BATCH PROCESSING PLAN")
        logger.info(f"{'='*60}")
        logger.info(f"Total URLs: {len(urls)}")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"Total batches: {total_batches}")
        logger.info(f"Processing batches: {batch_start} to {batch_end-1}")
        logger.info(f"Resume mode: {resume}")
        logger.info(f"{'='*60}\n")
        
        # Process batches
        start_time = datetime.now()
        
        for batch_num in range(batch_start, batch_end):
            # Get URLs for this batch
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(urls))
            batch_urls = urls[start_idx:end_idx]
            
            if not batch_urls:
                logger.info(f"No URLs for batch {batch_num}, stopping")
                break
            
            # Process batch
            try:
                self.process_batch(batch_num, batch_urls)
            except KeyboardInterrupt:
                logger.warning("\n⚠ Interrupted by user. Progress saved.")
                break
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {e}")
                continue
        
        # Final statistics
        elapsed = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"PROCESSING COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Total processed: {self.metadata['total_processed']}")
        logger.info(f"Successful: {self.metadata['total_successful']}")
        logger.info(f"Failed: {self.metadata['total_failed']}")
        if self.metadata['total_processed'] > 0:
            logger.info(f"Success rate: {self.metadata['total_successful']/self.metadata['total_processed']*100:.1f}%")
            logger.info(f"Time elapsed: {elapsed/60:.1f} minutes")
            logger.info(f"Average time per property: {elapsed/self.metadata['total_processed']:.1f}s")
        logger.info(f"{'='*60}\n")
        
        return self.metadata
    
    def close(self):
        """Close the scraper and clean up resources."""
        if hasattr(self.scraper, 'browser') and self.scraper.browser:
            self.scraper.browser.close()
        if hasattr(self.scraper, 'playwright') and self.scraper.playwright:
            self.scraper.playwright.stop()


if __name__ == "__main__":
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch process property URLs")
    parser.add_argument("--input", required=True, help="Input CSV file with URLs")
    parser.add_argument("--output", required=True, help="Output directory for Parquet files")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size (default: 100)")
    parser.add_argument("--batch-start", type=int, help="Starting batch number")
    parser.add_argument("--batch-end", type=int, help="Ending batch number")
    parser.add_argument("--no-resume", action="store_true", help="Don't resume from last batch")
    parser.add_argument("--no-headless", action="store_true", help="Show browser")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create and run batch manager
    manager = BatchManager(
        input_file=args.input,
        output_dir=args.output,
        batch_size=args.batch_size,
        headless=not args.no_headless
    )
    
    try:
        manager.process_all(
            batch_start=args.batch_start,
            batch_end=args.batch_end,
            resume=not args.no_resume
        )
    finally:
        manager.close()
