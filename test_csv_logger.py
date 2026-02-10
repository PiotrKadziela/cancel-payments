#!/usr/bin/env python3
"""
Test script for CSV Progress Logger functionality
"""

import os
import sys
import tempfile
import csv
from datetime import datetime

# Add parent directory to path to import cancel_payments module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cancel_payments import (
    CSVProgressLogger,
    CSV_HEADERS,
    STATUS_FETCHED,
    STATUS_NO_ACTION,
    STATUS_SUCCESS,
    STATUS_ERROR
)


def test_csv_creation():
    """Test CSV file creation with headers"""
    print("Test 1: CSV file creation...")
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
        tmp_path = tmp.name
    
    try:
        # Remove the file so CSVProgressLogger can create it
        os.unlink(tmp_path)
        
        logger = CSVProgressLogger(tmp_path)
        
        # Check file exists
        assert os.path.exists(tmp_path), "CSV file was not created"
        
        # Check headers
        with open(tmp_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert headers == CSV_HEADERS, f"Headers mismatch: {headers}"
        
        print("✓ CSV file creation test passed")
        return True
        
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_write_single_order():
    """Test writing a single order to CSV"""
    print("\nTest 2: Writing single order...")
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
        tmp_path = tmp.name
    
    try:
        os.unlink(tmp_path)
        logger = CSVProgressLogger(tmp_path)
        
        # Write an order
        logger.write_order('100001234', STATUS_FETCHED)
        
        # Read back and verify
        orders = logger.read_all_orders()
        assert '100001234' in orders, "Order not found in CSV"
        assert orders['100001234']['status'] == STATUS_FETCHED
        assert orders['100001234']['payment_id'] == ''
        assert orders['100001234']['error_message'] == ''
        
        print("✓ Single order write test passed")
        return True
        
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_update_order():
    """Test updating an existing order"""
    print("\nTest 3: Updating existing order...")
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
        tmp_path = tmp.name
    
    try:
        os.unlink(tmp_path)
        logger = CSVProgressLogger(tmp_path)
        
        # Write initial order
        logger.write_order('100001234', STATUS_FETCHED)
        
        # Update the order
        logger.write_order('100001234', STATUS_SUCCESS, payment_id='98765')
        
        # Read and verify
        orders = logger.read_all_orders()
        assert orders['100001234']['status'] == STATUS_SUCCESS
        assert orders['100001234']['payment_id'] == '98765'
        
        print("✓ Order update test passed")
        return True
        
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_bulk_write():
    """Test bulk writing multiple orders"""
    print("\nTest 4: Bulk writing orders...")
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
        tmp_path = tmp.name
    
    try:
        os.unlink(tmp_path)
        logger = CSVProgressLogger(tmp_path)
        
        # Bulk write
        order_ids = ['100001234', '100001235', '100001236']
        logger.bulk_write_orders(order_ids, STATUS_FETCHED)
        
        # Verify all orders
        orders = logger.read_all_orders()
        assert len(orders) == 3, f"Expected 3 orders, got {len(orders)}"
        
        for order_id in order_ids:
            assert order_id in orders, f"Order {order_id} not found"
            assert orders[order_id]['status'] == STATUS_FETCHED
        
        print("✓ Bulk write test passed")
        return True
        
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_filtering_orders():
    """Test filtering already processed orders"""
    print("\nTest 5: Filtering processed orders...")
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
        tmp_path = tmp.name
    
    try:
        os.unlink(tmp_path)
        logger = CSVProgressLogger(tmp_path)
        
        # Setup: some orders with different statuses
        logger.write_order('100001234', STATUS_SUCCESS, payment_id='98765')
        logger.write_order('100001235', STATUS_NO_ACTION)
        logger.write_order('100001236', STATUS_FETCHED)
        logger.write_order('100001237', STATUS_ERROR, payment_id='98766', error_message='Test error')
        
        # All orders (including new ones)
        all_orders = ['100001234', '100001235', '100001236', '100001237', '100001238', '100001239']
        
        # Get orders to process
        to_process = logger.get_orders_to_process(all_orders)
        
        # Should process: 100001236 (fetched), 100001238 (new), 100001239 (new)
        # Should skip: 100001234 (success), 100001235 (no_action), 100001237 (error)
        expected = ['100001236', '100001238', '100001239']
        
        assert set(to_process) == set(expected), f"Expected {expected}, got {to_process}"
        
        print("✓ Order filtering test passed")
        return True
        
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_error_handling():
    """Test error message storage"""
    print("\nTest 6: Error message handling...")
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
        tmp_path = tmp.name
    
    try:
        os.unlink(tmp_path)
        logger = CSVProgressLogger(tmp_path)
        
        # Write order with error
        error_msg = 'API returned 500: Internal Server Error'
        logger.write_order('100001234', STATUS_ERROR, payment_id='98765', error_message=error_msg)
        
        # Read and verify
        orders = logger.read_all_orders()
        assert orders['100001234']['error_message'] == error_msg
        
        print("✓ Error message handling test passed")
        return True
        
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_csv_format():
    """Test CSV format with special characters"""
    print("\nTest 7: CSV format with special characters...")
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
        tmp_path = tmp.name
    
    try:
        os.unlink(tmp_path)
        logger = CSVProgressLogger(tmp_path)
        
        # Write order with special characters in error message
        error_msg = 'Error: "Connection failed", status: 500, message: comma,separated,values'
        logger.write_order('100001234', STATUS_ERROR, payment_id='98765', error_message=error_msg)
        
        # Read back
        orders = logger.read_all_orders()
        assert orders['100001234']['error_message'] == error_msg
        
        print("✓ CSV format test passed")
        return True
        
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_timestamp_format():
    """Test timestamp format in CSV"""
    print("\nTest 8: Timestamp format...")
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
        tmp_path = tmp.name
    
    try:
        os.unlink(tmp_path)
        logger = CSVProgressLogger(tmp_path)
        
        # Write order
        logger.write_order('100001234', STATUS_FETCHED)
        
        # Read and verify timestamp format
        orders = logger.read_all_orders()
        timestamp = orders['100001234']['timestamp']
        
        # Try parsing as ISO 8601
        try:
            datetime.fromisoformat(timestamp)
            print("✓ Timestamp format test passed")
            return True
        except ValueError:
            print(f"✗ Invalid timestamp format: {timestamp}")
            return False
        
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Running CSV Progress Logger Tests")
    print("=" * 60)
    
    tests = [
        test_csv_creation,
        test_write_single_order,
        test_update_order,
        test_bulk_write,
        test_filtering_orders,
        test_error_handling,
        test_csv_format,
        test_timestamp_format
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Tests completed: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
