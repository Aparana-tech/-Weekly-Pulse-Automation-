import schedule
import time
import subprocess
import logging
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("scheduler")

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VENV_PYTHON = os.path.join(PROJECT_DIR, ".venv", "bin", "python3")

def run_pulse_pipeline():
    """Runs the main pulse pipeline."""
    logger.info("⏰ Starting automated Pulse pipeline run...")
    try:
        # Run the pipeline using the virtual environment python
        result = subprocess.run(
            [VENV_PYTHON, "src/main.py", "run", "--all", "--force"],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ Automated Pulse pipeline completed successfully!")
            logger.debug(f"Output:\n{result.stdout}")
        else:
            logger.error(f"❌ Automated Pulse pipeline failed with exit code {result.returncode}")
            logger.error(f"Error Output:\n{result.stderr}")
            
    except Exception as e:
        logger.error(f"❌ Failed to execute pipeline: {e}")

def main():
    logger.info("🚀 Pulse Automated Scheduler Started")
    logger.info("The pipeline is scheduled to run every Monday at 06:00 AM.")
    
    # Schedule the job every Monday at 6:00 AM
    schedule.every().monday.at("06:00").do(run_pulse_pipeline)
    
    # For testing purposes, you can uncomment the line below to run it every 1 minute instead
    # schedule.every(1).minutes.do(run_pulse_pipeline)
    
    logger.info("Waiting for the next scheduled run... (Press Ctrl+C to exit)")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60) # Check every 60 seconds
    except KeyboardInterrupt:
        logger.info("🛑 Scheduler stopped by user.")

if __name__ == "__main__":
    main()
