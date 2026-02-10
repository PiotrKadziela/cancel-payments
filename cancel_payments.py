#!/usr/bin/env python3
"""
Cancel Payments Script
Automatically cancels payments in Papaya system for orders canceled in Magento.
"""

import os
import sys
import logging
import csv
from typing import List, Tuple, Dict, Optional
from datetime import datetime

import pymysql
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('cancel_payments.log')
    ]
)
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Helper class for managing database connections."""
    
    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None
    
    def __enter__(self):
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info(f"Connected to database: {self.database}")
            return self.connection
        except pymysql.Error as e:
            logger.error(f"Failed to connect to database {self.database}: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.close()
            logger.info(f"Closed connection to database: {self.database}")


def load_configuration() -> dict:
    """Load configuration from environment variables."""
    load_dotenv()
    
    try:
        magento_port = int(os.getenv('MAGENTO_DB_PORT', 3306))
        papaya_port = int(os.getenv('PAPAYA_DB_PORT', 3306))
    except ValueError as e:
        logger.error(f"Invalid port number in configuration: {e}")
        raise ValueError(f"Database port must be a valid integer: {e}")
    
    config = {
        'magento': {
            'host': os.getenv('MAGENTO_DB_HOST'),
            'port': magento_port,
            'database': os.getenv('MAGENTO_DB_NAME'),
            'user': os.getenv('MAGENTO_DB_USER'),
            'password': os.getenv('MAGENTO_DB_PASSWORD'),
        },
        'papaya': {
            'host': os.getenv('PAPAYA_DB_HOST'),
            'port': papaya_port,
            'database': os.getenv('PAPAYA_DB_NAME'),
            'user': os.getenv('PAPAYA_DB_USER'),
            'password': os.getenv('PAPAYA_DB_PASSWORD'),
        },
        'api': {
            'url': os.getenv('PAPAYA_API_URL'),
            'login': os.getenv('PAPAYA_API_LOGIN'),
            'password': os.getenv('PAPAYA_API_PASSWORD'),
        },
        'date_from': os.getenv('DATE_FROM'),
        'date_to': os.getenv('DATE_TO'),
    }
    
    # Validate required configuration
    required_fields = [
        'magento.host', 'magento.database', 'magento.user', 'magento.password',
        'papaya.host', 'papaya.database', 'papaya.user', 'papaya.password',
        'api.url', 'api.login', 'api.password',
        'date_from', 'date_to'
    ]
    
    for field in required_fields:
        parts = field.split('.')
        value = config
        for part in parts:
            value = value.get(part)
        
        if not value:
            logger.error(f"Missing required configuration: {field}")
            raise ValueError(f"Missing required configuration: {field}")
    
    # Validate date formats
    try:
        datetime.strptime(config['date_from'], '%Y-%m-%d')
        datetime.strptime(config['date_to'], '%Y-%m-%d')
    except ValueError as e:
        logger.error(f"Invalid date format (expected YYYY-MM-DD): {e}")
        raise
    
    logger.info(f"Configuration loaded successfully for date range: {config['date_from']} to {config['date_to']}")
    return config


def get_csv_filename(config: dict) -> str:
    """Generate CSV filename based on date range from configuration."""
    date_from = config['date_from'].replace('-', '')
    date_to = config['date_to'].replace('-', '')
    return f"payment_cancellation_status_{date_from}_to_{date_to}.csv"


def load_orders_from_csv(csv_filename: str) -> Dict[str, dict]:
    """
    Load existing orders from CSV file.
    
    Returns dictionary with order_id as key and order data as value.
    """
    if not os.path.exists(csv_filename):
        logger.info(f"CSV file {csv_filename} does not exist")
        return {}
    
    orders_data = {}
    try:
        with open(csv_filename, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                order_id = row['order_id']
                # Convert string booleans to actual booleans
                row['requires_cancellation'] = row['requires_cancellation'] if row['requires_cancellation'] in ['True', 'False'] else None
                if row['requires_cancellation'] is not None:
                    row['requires_cancellation'] = row['requires_cancellation'] == 'True'
                row['cancellation_attempted'] = row['cancellation_attempted'] == 'True'
                orders_data[order_id] = row
        
        logger.info(f"Loaded {len(orders_data)} orders from CSV: {csv_filename}")
        return orders_data
    except Exception as e:
        logger.error(f"Error loading orders from CSV {csv_filename}: {e}")
        raise


def save_orders_to_csv(csv_filename: str, orders_data: Dict[str, dict]) -> None:
    """Save all orders to CSV file."""
    try:
        fieldnames = ['order_id', 'payment_id', 'requires_cancellation', 
                     'cancellation_attempted', 'cancellation_status', 
                     'error_message', 'timestamp']
        
        with open(csv_filename, 'w', encoding='utf-8', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            for order_id in sorted(orders_data.keys()):
                order = orders_data[order_id]
                writer.writerow({
                    'order_id': order.get('order_id', order_id),
                    'payment_id': order.get('payment_id', ''),
                    'requires_cancellation': order.get('requires_cancellation', None),
                    'cancellation_attempted': order.get('cancellation_attempted', False),
                    'cancellation_status': order.get('cancellation_status', 'PENDING'),
                    'error_message': order.get('error_message', ''),
                    'timestamp': order.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                })
        
        logger.info(f"Saved {len(orders_data)} orders to CSV: {csv_filename}")
    except Exception as e:
        logger.error(f"Error saving orders to CSV {csv_filename}: {e}")
        raise


def update_order_in_csv(csv_filename: str, order_id: str, updates: dict) -> None:
    """
    Update a single order in CSV file.
    
    Loads entire CSV, updates the order, and saves back to file.
    """
    orders_data = load_orders_from_csv(csv_filename)
    
    if order_id not in orders_data:
        logger.warning(f"Order {order_id} not found in CSV")
        return
    
    # Update the order with new values
    orders_data[order_id].update(updates)
    orders_data[order_id]['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    save_orders_to_csv(csv_filename, orders_data)


def get_pending_orders_from_csv(csv_filename: str) -> List[str]:
    """
    Get list of order_ids that require processing.
    
    Returns orders where cancellation_attempted=False AND requires_cancellation=True.
    """
    orders_data = load_orders_from_csv(csv_filename)
    
    pending_orders = [
        order_id for order_id, order in orders_data.items()
        if not order.get('cancellation_attempted', False) 
        and order.get('requires_cancellation', False) is True
    ]
    
    logger.info(f"Found {len(pending_orders)} pending orders to process from CSV")
    return pending_orders


def get_canceled_orders_from_magento(config: dict, csv_filename: Optional[str] = None) -> List[str]:
    """
    Step 1: Get canceled orders from Magento database.
    
    Returns list of increment_ids for canceled orders.
    If csv_filename is provided, saves orders to CSV with initial status.
    """
    logger.info("Step 1: Fetching canceled orders from Magento...")
    
    query = """
        SELECT DISTINCT sfo.increment_id
        FROM sales_flat_order sfo
        INNER JOIN sales_flat_order_payment sfop 
          ON sfop.parent_id = sfo.entity_id
        WHERE sfo.status = 'canceled'
          AND sfo.created_at BETWEEN %s AND %s
          AND sfop.txn_id IS NOT NULL
          AND sfop.txn_id != ''
        GROUP BY sfo.increment_id
        HAVING COUNT(sfop.entity_id) > 1
    """
    
    db_config = config['magento']
    date_from = config['date_from']
    date_to = config['date_to']
    
    try:
        with DatabaseConnection(**db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (date_from, date_to))
                results = cursor.fetchall()
                
                increment_ids = [row['increment_id'] for row in results]
                logger.info(f"Found {len(increment_ids)} canceled orders in Magento")
                
                if increment_ids:
                    logger.debug(f"Order IDs: {increment_ids}")
                
                # Save to CSV if filename provided
                if csv_filename and increment_ids:
                    orders_data = {}
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    for order_id in increment_ids:
                        orders_data[order_id] = {
                            'order_id': order_id,
                            'payment_id': None,
                            'requires_cancellation': None,
                            'cancellation_attempted': False,
                            'cancellation_status': 'PENDING',
                            'error_message': '',
                            'timestamp': current_time
                        }
                    save_orders_to_csv(csv_filename, orders_data)
                    logger.info(f"Saved {len(increment_ids)} orders to CSV with initial status")
                
                return increment_ids
    except Exception as e:
        logger.error(f"Error fetching canceled orders from Magento: {e}")
        raise


def get_non_canceled_payments_from_papaya(config: dict, order_ids: List[str], 
                                          csv_filename: Optional[str] = None) -> Tuple[List[int], Dict[str, int]]:
    """
    Step 2: Find non-canceled payments in Papaya database.
    
    Returns tuple of (payment_ids list, order_id to payment_id mapping).
    If csv_filename is provided, updates CSV with payment_id info and requires_cancellation status.
    """
    if not order_ids:
        logger.info("Step 2: No orders to process, skipping Papaya query")
        return [], {}
    
    logger.info(f"Step 2: Fetching non-canceled payments from Papaya for {len(order_ids)} orders...")
    
    query = """
        SELECT pi.payment_id, pi.client_order_id
        FROM payment_information pi
        WHERE pi.client_order_id IN %s
          AND NOT EXISTS (
            SELECT 1 
            FROM payment_status_history psh
            WHERE psh.payment_id = pi.payment_id
              AND psh.status = 'canceled'
          )
    """
    
    db_config = config['papaya']
    
    try:
        with DatabaseConnection(**db_config) as conn:
            with conn.cursor() as cursor:
                # Use parameterized query to prevent SQL injection
                cursor.execute(query, (order_ids,))
                results = cursor.fetchall()
                
                payment_ids = [row['payment_id'] for row in results]
                order_to_payment_map = {row['client_order_id']: row['payment_id'] for row in results}
                
                logger.info(f"Found {len(payment_ids)} non-canceled payments in Papaya")
                
                if payment_ids:
                    logger.debug(f"Payment IDs: {payment_ids}")
                
                # Update CSV if filename provided
                if csv_filename:
                    orders_data = load_orders_from_csv(csv_filename)
                    
                    for order_id in order_ids:
                        if order_id in orders_data:
                            if order_id in order_to_payment_map:
                                # Order HAS payment_id in Papaya - requires cancellation
                                orders_data[order_id]['payment_id'] = order_to_payment_map[order_id]
                                orders_data[order_id]['requires_cancellation'] = True
                                orders_data[order_id]['cancellation_status'] = 'PENDING'
                            else:
                                # Order DOES NOT have payment_id in Papaya - no cancellation needed
                                orders_data[order_id]['payment_id'] = ''
                                orders_data[order_id]['requires_cancellation'] = False
                                orders_data[order_id]['cancellation_status'] = 'NOT_REQUIRED'
                            
                            orders_data[order_id]['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    save_orders_to_csv(csv_filename, orders_data)
                    logger.info(f"Updated CSV with payment information for {len(order_ids)} orders")
                
                return payment_ids, order_to_payment_map
    except Exception as e:
        logger.error(f"Error fetching non-canceled payments from Papaya: {e}")
        raise


def cancel_payment_via_api(config: dict, payment_id: int) -> Tuple[bool, str]:
    """
    Cancel a single payment via Papaya API.
    
    Returns tuple of (success: bool, message: str)
    """
    api_url = f"{config['api']['url']}/api/v1/payments/{payment_id}/cancel"
    auth = HTTPBasicAuth(config['api']['login'], config['api']['password'])
    
    try:
        response = requests.post(api_url, auth=auth, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"Successfully canceled payment {payment_id}")
            return True, "Success"
        else:
            error_msg = f"API returned status {response.status_code}"
            try:
                error_detail = response.json()
                error_msg += f": {error_detail}"
            except (ValueError, requests.exceptions.JSONDecodeError):
                error_msg += f": {response.text}"
            
            logger.error(f"Failed to cancel payment {payment_id}: {error_msg}")
            return False, error_msg
    except requests.exceptions.Timeout:
        error_msg = "Request timeout"
        logger.error(f"Failed to cancel payment {payment_id}: {error_msg}")
        return False, error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"Request error: {str(e)}"
        logger.error(f"Failed to cancel payment {payment_id}: {error_msg}")
        return False, error_msg


def cancel_payments_via_api(config: dict, payment_ids: List[int], 
                            payment_to_order_map: Optional[Dict[int, str]] = None,
                            csv_filename: Optional[str] = None) -> dict:
    """
    Step 3: Cancel payments via Papaya API.
    
    Returns dictionary with statistics.
    If csv_filename is provided, updates CSV after each cancellation attempt.
    """
    if not payment_ids:
        logger.info("Step 3: No payments to cancel")
        return {'total': 0, 'success': 0, 'failed': 0}
    
    logger.info(f"Step 3: Canceling {len(payment_ids)} payments via Papaya API...")
    
    stats = {
        'total': len(payment_ids),
        'success': 0,
        'failed': 0,
        'errors': []
    }
    
    for payment_id in payment_ids:
        success, message = cancel_payment_via_api(config, payment_id)
        
        if success:
            stats['success'] += 1
        else:
            stats['failed'] += 1
            stats['errors'].append({
                'payment_id': payment_id,
                'error': message
            })
        
        # Update CSV if filename and mapping provided
        if csv_filename and payment_to_order_map and payment_id in payment_to_order_map:
            order_id = payment_to_order_map[payment_id]
            updates = {
                'cancellation_attempted': True,
                'cancellation_status': 'SUCCESS' if success else 'FAILED',
                'error_message': '' if success else message
            }
            update_order_in_csv(csv_filename, order_id, updates)
    
    logger.info(f"Cancellation complete: {stats['success']} succeeded, {stats['failed']} failed")
    
    if stats['errors']:
        logger.warning(f"Errors encountered: {stats['errors']}")
    
    return stats


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("Starting Payment Cancellation Script")
    logger.info("=" * 80)
    
    try:
        # Load configuration
        config = load_configuration()
        
        # Generate CSV filename
        csv_filename = get_csv_filename(config)
        logger.info(f"CSV filename: {csv_filename}")
        
        # Check if CSV exists for resuming
        resume_mode = os.path.exists(csv_filename)
        
        if resume_mode:
            logger.info("=" * 80)
            logger.info("RESUME MODE: CSV file found, resuming from previous run")
            logger.info("=" * 80)
            
            # Load existing orders
            orders_data = load_orders_from_csv(csv_filename)
            
            # Get pending orders that need processing
            pending_order_ids = get_pending_orders_from_csv(csv_filename)
            
            if not pending_order_ids:
                logger.info("No pending orders to process. All orders have been handled.")
                
                # Generate final statistics
                total_orders = len(orders_data)
                requires_cancellation = sum(1 for o in orders_data.values() if o.get('requires_cancellation') is True)
                not_required = sum(1 for o in orders_data.values() if o.get('cancellation_status') == 'NOT_REQUIRED')
                successful = sum(1 for o in orders_data.values() if o.get('cancellation_status') == 'SUCCESS')
                failed = sum(1 for o in orders_data.values() if o.get('cancellation_status') == 'FAILED')
                
                logger.info("=" * 80)
                logger.info("Payment Cancellation Summary (from CSV):")
                logger.info(f"  Total orders in CSV: {total_orders}")
                logger.info(f"  Orders requiring cancellation: {requires_cancellation}")
                logger.info(f"  Orders not requiring cancellation: {not_required}")
                logger.info(f"  Payments successfully canceled: {successful}")
                logger.info(f"  Payments failed to cancel: {failed}")
                logger.info(f"  CSV file location: {os.path.abspath(csv_filename)}")
                logger.info("=" * 80)
                logger.info("Script completed - all orders already processed")
                sys.exit(0)
            
            logger.info(f"Resuming processing for {len(pending_order_ids)} pending orders")
            
            # Step 2: Find non-canceled payments in Papaya (only for pending orders)
            non_canceled_payments, order_to_payment_map = get_non_canceled_payments_from_papaya(
                config, pending_order_ids, csv_filename
            )
            
            # Create reverse mapping (payment_id -> order_id) for CSV updates
            payment_to_order_map = {v: k for k, v in order_to_payment_map.items()}
            
            # Step 3: Cancel payments via API
            stats = cancel_payments_via_api(config, non_canceled_payments, payment_to_order_map, csv_filename)
            
            # Reload orders data for final statistics
            orders_data = load_orders_from_csv(csv_filename)
            
        else:
            logger.info("=" * 80)
            logger.info("NEW RUN MODE: No CSV file found, starting fresh")
            logger.info("=" * 80)
            
            # Step 1: Get canceled orders from Magento
            canceled_orders = get_canceled_orders_from_magento(config, csv_filename)
            
            # Step 2: Find non-canceled payments in Papaya
            non_canceled_payments, order_to_payment_map = get_non_canceled_payments_from_papaya(
                config, canceled_orders, csv_filename
            )
            
            # Create reverse mapping (payment_id -> order_id) for CSV updates
            payment_to_order_map = {v: k for k, v in order_to_payment_map.items()}
            
            # Step 3: Cancel payments via API
            stats = cancel_payments_via_api(config, non_canceled_payments, payment_to_order_map, csv_filename)
            
            # Load final data from CSV for statistics
            orders_data = load_orders_from_csv(csv_filename)
        
        # Generate final statistics from CSV
        total_orders = len(orders_data)
        requires_cancellation = sum(1 for o in orders_data.values() if o.get('requires_cancellation') is True)
        not_required = sum(1 for o in orders_data.values() if o.get('cancellation_status') == 'NOT_REQUIRED')
        successful = sum(1 for o in orders_data.values() if o.get('cancellation_status') == 'SUCCESS')
        failed = sum(1 for o in orders_data.values() if o.get('cancellation_status') == 'FAILED')
        
        # Summary
        logger.info("=" * 80)
        logger.info("Payment Cancellation Summary:")
        logger.info(f"  Total orders in CSV: {total_orders}")
        logger.info(f"  Orders requiring cancellation: {requires_cancellation}")
        logger.info(f"  Orders not requiring cancellation: {not_required}")
        logger.info(f"  Payments successfully canceled: {successful}")
        logger.info(f"  Payments failed to cancel: {failed}")
        logger.info(f"  CSV file location: {os.path.abspath(csv_filename)}")
        logger.info("=" * 80)
        
        if failed > 0:
            logger.warning("Some payments failed to cancel. Check the log and CSV file for details.")
            sys.exit(1)
        else:
            logger.info("Script completed successfully")
            sys.exit(0)
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
