#!/usr/bin/env python3
"""
Phase 2 Master Runner - Coordinates all Tier 2 scrapers with multi-threading.
Runs enhanced scraper, web search, blog/news scraper, and GitHub analyzer in parallel.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import time
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_scraper(scraper_name, script_path):
    """Run a scraper script and capture output."""
    logger.info(f"Starting {scraper_name}...")
    start_time = time.time()
    
    try:
        # Run the scraper
        result = subprocess.run(
            ['python', script_path],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes timeout per scraper
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            logger.info(f"✓ {scraper_name} completed successfully in {elapsed:.1f}s")
            return {
                'name': scraper_name,
                'status': 'success',
                'elapsed': elapsed,
                'output': result.stdout[-1000:]  # Last 1000 chars
            }
        else:
            logger.error(f"✗ {scraper_name} failed with code {result.returncode}")
            logger.error(f"Error: {result.stderr[-500:]}")
            return {
                'name': scraper_name,
                'status': 'failed',
                'elapsed': elapsed,
                'error': result.stderr[-500:]
            }
            
    except subprocess.TimeoutExpired:
        logger.warning(f"⚠ {scraper_name} timed out after 30 minutes")
        return {
            'name': scraper_name,
            'status': 'timeout',
            'elapsed': 1800
        }
    except Exception as e:
        logger.error(f"✗ {scraper_name} error: {str(e)}")
        return {
            'name': scraper_name,
            'status': 'error',
            'error': str(e)
        }

def main():
    """Run all Phase 2 scrapers in parallel."""
    logger.info("="*70)
    logger.info("PHASE 2: Advanced Web Scraping - Starting all Tier 2 scrapers")
    logger.info("="*70)
    
    start_time = datetime.now()
    
    # Define scrapers to run
    scrapers = [
        ('Enhanced Gap Filler', 'scripts/run_enhanced_scraping.py'),
        ('Web Search Crawler', 'scripts/web_search_crawler.py'),
        ('Blog/News Scraper', 'scripts/blog_news_scraper.py'),
        ('GitHub Analyzer', 'scripts/github_analyzer.py')
    ]
    
    # Check if scripts exist
    for name, path in scrapers:
        if not os.path.exists(path):
            logger.warning(f"Script not found: {path}")
    
    logger.info(f"Running {len(scrapers)} scrapers in parallel with multi-threading...")
    logger.info("This may take 15-30 minutes. Progress will be shown as scrapers complete.\n")
    
    # Run scrapers in parallel
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all scrapers
        future_to_scraper = {
            executor.submit(run_scraper, name, path): (name, path) 
            for name, path in scrapers
        }
        
        # Process results as they complete
        for future in as_completed(future_to_scraper):
            scraper_name, _ = future_to_scraper[future]
            try:
                result = future.result()
                results.append(result)
                
                # Show progress
                completed = len(results)
                total = len(scrapers)
                logger.info(f"Progress: {completed}/{total} scrapers completed")
                
            except Exception as e:
                logger.error(f"Unexpected error with {scraper_name}: {e}")
                results.append({
                    'name': scraper_name,
                    'status': 'error',
                    'error': str(e)
                })
    
    # Summary
    elapsed_total = (datetime.now() - start_time).total_seconds()
    
    logger.info("\n" + "="*70)
    logger.info("PHASE 2 COMPLETE - Summary")
    logger.info("="*70)
    logger.info(f"Total time: {elapsed_total:.1f} seconds ({elapsed_total/60:.1f} minutes)")
    logger.info(f"Scrapers run: {len(scrapers)}")
    
    # Status breakdown
    success_count = sum(1 for r in results if r['status'] == 'success')
    failed_count = sum(1 for r in results if r['status'] == 'failed')
    timeout_count = sum(1 for r in results if r['status'] == 'timeout')
    
    logger.info(f"✓ Successful: {success_count}")
    logger.info(f"✗ Failed: {failed_count}")
    logger.info(f"⚠ Timed out: {timeout_count}")
    
    # Detailed results
    logger.info("\nDetailed Results:")
    for result in sorted(results, key=lambda x: x['name']):
        status_symbol = {
            'success': '✓',
            'failed': '✗',
            'timeout': '⚠',
            'error': '✗'
        }.get(result['status'], '?')
        
        logger.info(f"{status_symbol} {result['name']}: {result['status']}")
        if 'elapsed' in result:
            logger.info(f"  Time: {result['elapsed']:.1f}s")
        if 'error' in result:
            logger.info(f"  Error: {result['error'][:100]}...")
    
    logger.info("\n" + "="*70)
    logger.info("Phase 2 scraping complete. Check the database for updated model information.")
    logger.info("Next step: Run Phase 3 for dashboard development.")
    logger.info("="*70)

if __name__ == "__main__":
    main()