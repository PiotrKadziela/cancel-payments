#!/usr/bin/env python3
"""
Cancel Payments Script with CSV Progress Logging

This script cancels payments for canceled orders in Magento by:
1. Fetching canceled orders from Magento database
2. Checking Papaya database for associated payments
3. Canceling payments via Papaya API
4. Logging progress to CSV for safe interruption and resumption
"""

import csv
import logging
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional

import mysql.connector
import requests
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Configure logging
LOG_FILE = os.getenv('LOG_FILE', 'cancel_payments.log')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# CSV Configuration
PROGRESS_LOG_FILE = os.getenv('PROGRESS_LOG_FILE', 'progress_log.csv')
CSV_HEADERS = ['order_increment_id', 'timestamp', 'status', 'payment_id', 'error_message']

# Status constants
STATUS_FETCHED = 'fetched_from_magento'
STATUS_NO_ACTION = 'no_action_needed'
STATUS_SUCCESS = 'payment_canceled_success'
STATUS_ERROR = 'payment_canceled_error'


class CSVProgressLogger:
    """
    Handles CSV-based progress logging for order processing.
    
    Provides atomic operations for reading and writing order statuses
    to ensure safe interruption and resumption of the script.
    """
    
    def __init__(self, csv_file: str):
        """
        Initialize CSV progress logger.
        
        Args:
            csv_file: Path to the CSV file for progress logging
        """
        self.csv_file = csv_file
        self._ensure_csv_exists()
    
    def _ensure_csv_exists(self):
        """Create CSV file with headers if it doesn't exist."""
        if not os.path.exists(self.csv_file):
            try:
                with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                    writer.writeheader()
                logger.info(f"Created new progress log file: {self.csv_file}")
            except Exception as e:
                logger.error(f"Failed to create CSV file {self.csv_file}: {e}")
                raise
    
    def read_all_orders(self) -> Dict[str, Dict[str, str]]:
        """
        Read all orders from CSV file.
        
        Returns:
            Dictionary mapping order_increment_id to order data
        """
        orders = {}
        
        if not os.path.exists(self.csv_file):
            return orders
        
        try:
            with open(self.csv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    order_id = row['order_increment_id']
                    orders[order_id] = row
            logger.info(f"Loaded {len(orders)} orders from CSV")
        except Exception as e:
            logger.warning(f"Failed to read CSV file {self.csv_file}: {e}. Starting fresh.")
            orders = {}
        
        return orders
    
    def write_order(self, order_increment_id: str, status: str, 
                   payment_id: str = '', error_message: str = ''):
        """
        Write or update a single order in the CSV file.
        
        This method performs an atomic update by:
        1. Reading the entire file
        2. Updating the relevant row
        3. Writing the entire file back
        
        Args:
            order_increment_id: Magento order ID
            status: Processing status
            payment_id: Papaya payment ID (optional)
            error_message: Error details (optional)
        """
        timestamp = datetime.utcnow().isoformat()
        
        try:
            # Read all existing orders
            orders = self.read_all_orders()
            
            # Update or add the order
            orders[order_increment_id] = {
                'order_increment_id': order_increment_id,
                'timestamp': timestamp,
                'status': status,
                'payment_id': payment_id,
                'error_message': error_message
            }
            
            # Write all orders back to file
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                writer.writeheader()
                for order_data in orders.values():
                    writer.writerow(order_data)
                f.flush()  # Ensure immediate write to disk
                os.fsync(f.fileno())  # Force write to disk
            
            logger.info(f"Updated CSV: order={order_increment_id}, status={status}")
            
        except Exception as e:
            logger.error(f"Failed to write to CSV for order {order_increment_id}: {e}")
            # Don't raise - continue processing even if CSV write fails
    
    def bulk_write_orders(self, order_ids: List[str], status: str):
        """
        Write multiple orders to CSV at once.
        
        Args:
            order_ids: List of order increment IDs
            status: Status to set for all orders
        """
        if not order_ids:
            return
        
        timestamp = datetime.utcnow().isoformat()
        
        try:
            # Read existing orders
            orders = self.read_all_orders()
            
            # Add new orders
            for order_id in order_ids:
                if order_id not in orders:
                    orders[order_id] = {
                        'order_increment_id': order_id,
                        'timestamp': timestamp,
                        'status': status,
                        'payment_id': '',
                        'error_message': ''
                    }
            
            # Write all orders back
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                writer.writeheader()
                for order_data in orders.values():
                    writer.writerow(order_data)
                f.flush()
                os.fsync(f.fileno())
            
            logger.info(f"Bulk wrote {len(order_ids)} orders to CSV with status={status}")
            
        except Exception as e:
            logger.error(f"Failed to bulk write to CSV: {e}")
    
    def get_orders_to_process(self, all_order_ids: List[str]) -> List[str]:
        """
        Filter orders to only process new or incomplete ones.
        
        Returns orders that are:
        - Not in CSV file yet, OR
        - Have status 'fetched_from_magento' (incomplete from previous run)
        
        Args:
            all_order_ids: All order IDs from Magento
            
        Returns:
            List of order IDs to process
        """
        existing_orders = self.read_all_orders()
        
        to_process = []
        skipped = 0
        
        for order_id in all_order_ids:
            if order_id not in existing_orders:
                # New order - needs processing
                to_process.append(order_id)
            elif existing_orders[order_id]['status'] == STATUS_FETCHED:
                # Incomplete order - needs processing
                to_process.append(order_id)
            else:
                # Already processed - skip
                skipped += 1
        
        logger.info(f"Orders loaded from CSV: {len(existing_orders)}")
        logger.info(f"Orders skipped (already processed): {skipped}")
        logger.info(f"Orders to process: {len(to_process)}")
        
        return to_process


class DatabaseConnection:
    """Database connection manager with context manager support."""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.config = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database
        }
        self.connection = None
    
    def __enter__(self):
        self.connection = mysql.connector.connect(**self.config)
        return self.connection
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.close()


def get_magento_connection():
    """Create Magento database connection."""
    return DatabaseConnection(
        host=os.getenv('MAGENTO_DB_HOST', 'localhost'),
        port=int(os.getenv('MAGENTO_DB_PORT', 3306)),
        user=os.getenv('MAGENTO_DB_USER'),
        password=os.getenv('MAGENTO_DB_PASSWORD'),
        database=os.getenv('MAGENTO_DB_NAME')
    )


def get_papaya_connection():
    """Create Papaya database connection."""
    return DatabaseConnection(
        host=os.getenv('PAPAYA_DB_HOST', 'localhost'),
        port=int(os.getenv('PAPAYA_DB_PORT', 3306)),
        user=os.getenv('PAPAYA_DB_USER'),
        password=os.getenv('PAPAYA_DB_PASSWORD'),
        database=os.getenv('PAPAYA_DB_NAME')
    )


def fetch_canceled_orders_from_magento() -> List[str]:
    """
    Fetch list of canceled order IDs from Magento database.
    
    Returns:
        List of order increment IDs
    """
    logger.info("Fetching canceled orders from Magento database...")
    
    query = """
        SELECT increment_id 
        FROM sales_order 
        WHERE status = 'canceled' 
        ORDER BY created_at DESC
    """
    
    try:
        with get_magento_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            orders = [row[0] for row in cursor.fetchall()]
            cursor.close()
        
        logger.info(f"Fetched {len(orders)} canceled orders from Magento")
        return orders
        
    except Exception as e:
        logger.error(f"Failed to fetch orders from Magento: {e}")
        raise


def get_payments_for_order(order_increment_id: str) -> List[Dict[str, any]]:
    """
    Get payments for an order from Papaya database.
    
    Args:
        order_increment_id: Magento order ID
        
    Returns:
        List of payment dictionaries with id and status
    """
    query = """
        SELECT payment_id, status 
        FROM payments 
        WHERE order_increment_id = %s 
        AND status != 'canceled'
    """
    
    try:
        with get_papaya_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, (order_increment_id,))
            payments = cursor.fetchall()
            cursor.close()
        
        return payments
        
    except Exception as e:
        logger.error(f"Failed to fetch payments for order {order_increment_id}: {e}")
        return []


def cancel_payment_via_api(payment_id: str) -> tuple[bool, Optional[str]]:
    """
    Cancel a payment via Papaya API.
    
    Args:
        payment_id: Papaya payment ID
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    api_url = os.getenv('PAPAYA_API_URL')
    api_key = os.getenv('PAPAYA_API_KEY')
    
    if not api_url or not api_key:
        error_msg = "Missing PAPAYA_API_URL or PAPAYA_API_KEY in environment"
        logger.error(error_msg)
        return False, error_msg
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'payment_id': payment_id,
        'action': 'cancel'
    }
    
    try:
        logger.info(f"Canceling payment {payment_id} via API...")
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"Successfully canceled payment {payment_id}")
            return True, None
        else:
            error_msg = f"API returned {response.status_code}: {response.text}"
            logger.error(f"Failed to cancel payment {payment_id}: {error_msg}")
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Exception during API call: {str(e)}"
        logger.error(f"Failed to cancel payment {payment_id}: {error_msg}")
        return False, error_msg


def process_order(order_increment_id: str, csv_logger: CSVProgressLogger):
    """
    Process a single order: check for payments and cancel if needed.
    
    Args:
        order_increment_id: Magento order ID
        csv_logger: CSV progress logger instance
    """
    logger.info(f"Processing order: {order_increment_id}")
    
    # Step 3: Check Papaya database for payments
    payments = get_payments_for_order(order_increment_id)
    
    if not payments:
        # No payments to cancel
        logger.info(f"Order {order_increment_id}: No payments to cancel")
        csv_logger.write_order(order_increment_id, STATUS_NO_ACTION)
        return
    
    logger.info(f"Order {order_increment_id}: Found {len(payments)} payment(s) to cancel")
    
    # Step 4: Cancel each payment via API
    for payment in payments:
        payment_id = str(payment['payment_id'])
        
        success, error_message = cancel_payment_via_api(payment_id)
        
        # Immediately update CSV after each API call
        if success:
            csv_logger.write_order(
                order_increment_id, 
                STATUS_SUCCESS, 
                payment_id=payment_id
            )
        else:
            csv_logger.write_order(
                order_increment_id,
                STATUS_ERROR,
                payment_id=payment_id,
                error_message=error_message or ''
            )


def main():
    """Main script execution."""
    logger.info("=" * 80)
    logger.info("Starting Cancel Payments Script")
    logger.info("=" * 80)
    
    # Initialize CSV logger
    csv_logger = CSVProgressLogger(PROGRESS_LOG_FILE)
    
    try:
        # Step 1: Fetch orders from Magento
        all_orders = fetch_canceled_orders_from_magento()
        
        if not all_orders:
            logger.info("No canceled orders found in Magento")
            return
        
        # Immediately write all fetched orders to CSV
        logger.info("Writing fetched orders to CSV...")
        csv_logger.bulk_write_orders(all_orders, STATUS_FETCHED)
        
        # Step 2: Filter already processed orders
        orders_to_process = csv_logger.get_orders_to_process(all_orders)
        
        if not orders_to_process:
            logger.info("No orders to process (all already completed)")
            return
        
        # Process each order
        logger.info(f"Starting to process {len(orders_to_process)} orders...")
        
        for i, order_id in enumerate(orders_to_process, 1):
            logger.info(f"Processing order {i}/{len(orders_to_process)}: {order_id}")
            process_order(order_id, csv_logger)
        
        logger.info("=" * 80)
        logger.info("Cancel Payments Script Completed Successfully")
        logger.info("=" * 80)
        
    except KeyboardInterrupt:
        logger.warning("Script interrupted by user. Progress has been saved to CSV.")
        logger.info("Run the script again to resume from where it left off.")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Script failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
