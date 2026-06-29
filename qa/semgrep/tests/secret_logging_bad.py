import logging

logger = logging.getLogger(__name__)

def process_data(data):
    try:
        # Some operation that might fail
        raise ValueError("Invalid user configuration keys")
    except Exception as e:
        # Matches vulnerable pattern: logging raw exception object
        logger.error(e)
        print("Error details:", e)
