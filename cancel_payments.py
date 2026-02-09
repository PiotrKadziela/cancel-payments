#!/usr/bin/env python3
"""
Cancel Payments Script
Automatically cancels payments in Papaya system for orders canceled in Magento.
"""

import os
import sys
import logging
from typing import List, Tuple
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


def get_canceled_orders_from_magento(config: dict) -> List[str]:
    """
    Step 1: Get canceled orders from Magento database.
    
    Returns list of increment_ids for canceled orders.
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
                
                return increment_ids
    except Exception as e:
        logger.error(f"Error fetching canceled orders from Magento: {e}")
        raise


def get_non_canceled_payments_from_papaya(config: dict, order_ids: List[str]) -> List[int]:
    """
    Step 2: Find non-canceled payments in Papaya database.
    
    Returns list of payment_ids that need to be canceled.
    """
    if not order_ids:
        logger.info("Step 2: No orders to process, skipping Papaya query")
        return []
    
    logger.info(f"Step 2: Fetching non-canceled payments from Papaya for {len(order_ids)} orders...")
    
    query = """
        SELECT pi.payment_id
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
                logger.info(f"Found {len(payment_ids)} non-canceled payments in Papaya")
                
                if payment_ids:
                    logger.debug(f"Payment IDs: {payment_ids}")
                
                return payment_ids
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


def cancel_payments_via_api(config: dict, payment_ids: List[int]) -> dict:
    """
    Step 3: Cancel payments via Papaya API.
    
    Returns dictionary with statistics.
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
        
        # Step 1: Get canceled orders from Magento
        canceled_orders = get_canceled_orders_from_magento(config)
        
        # Step 2: Find non-canceled payments in Papaya
        non_canceled_payments = get_non_canceled_payments_from_papaya(config, canceled_orders)
        
        # Step 3: Cancel payments via API
        stats = cancel_payments_via_api(config, non_canceled_payments)
        
        # Summary
        logger.info("=" * 80)
        logger.info("Payment Cancellation Summary:")
        logger.info(f"  Canceled orders found in Magento: {len(canceled_orders)}")
        logger.info(f"  Non-canceled payments found in Papaya: {len(non_canceled_payments)}")
        logger.info(f"  Payments successfully canceled: {stats['success']}")
        logger.info(f"  Payments failed to cancel: {stats['failed']}")
        logger.info("=" * 80)
        
        if stats['failed'] > 0:
            logger.warning("Some payments failed to cancel. Check the log for details.")
            sys.exit(1)
        else:
            logger.info("Script completed successfully")
            sys.exit(0)
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
