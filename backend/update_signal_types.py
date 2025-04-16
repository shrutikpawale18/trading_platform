import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_signal_types():
    try:
        # Connect to the database
        conn = sqlite3.connect('trading.db')
        cursor = conn.cursor()
        
        # Update lowercase values to uppercase
        cursor.execute("UPDATE signals SET type = 'BUY' WHERE type = 'buy'")
        cursor.execute("UPDATE signals SET type = 'SELL' WHERE type = 'sell'")
        cursor.execute("UPDATE signals SET type = 'HOLD' WHERE type = 'hold'")
        
        # Commit the changes
        conn.commit()
        logger.info("Successfully updated signal types in the database")
        
    except Exception as e:
        logger.error(f"Error updating signal types: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    update_signal_types() 