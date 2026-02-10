#!/usr/bin/env python3
"""
Demo script to showcase CSV logging functionality

This script simulates the order processing flow without requiring
actual database connections or API access.
"""

import os
import sys
import time
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cancel_payments import (
    CSVProgressLogger,
    STATUS_FETCHED,
    STATUS_NO_ACTION,
    STATUS_SUCCESS,
    STATUS_ERROR
)


def demo_basic_flow():
    """Demonstrate basic CSV logging flow"""
    print("=" * 70)
    print("DEMO: Basic CSV Logging Flow")
    print("=" * 70)
    
    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
        csv_file = tmp.name
    
    try:
        os.unlink(csv_file)
        
        print(f"\nCreating CSV logger with file: {csv_file}")
        logger = CSVProgressLogger(csv_file)
        
        # Step 1: Simulate fetching orders from Magento
        print("\n--- Step 1: Fetching orders from Magento ---")
        magento_orders = ['100001234', '100001235', '100001236', '100001237']
        print(f"Fetched {len(magento_orders)} orders from Magento")
        
        # Immediately write all orders to CSV
        print("\n--- Writing all orders to CSV with 'fetched_from_magento' status ---")
        logger.bulk_write_orders(magento_orders, STATUS_FETCHED)
        time.sleep(0.5)
        
        # Step 2: Filter already processed orders
        print("\n--- Step 2: Filtering already processed orders ---")
        to_process = logger.get_orders_to_process(magento_orders)
        print(f"Orders to process: {len(to_process)}")
        
        # Step 3 & 4: Process each order
        print("\n--- Step 3 & 4: Processing each order ---")
        
        # Order 1: No payments to cancel
        print(f"\nProcessing order {to_process[0]}...")
        print("  → Checking Papaya database...")
        time.sleep(0.3)
        print("  → No payments found")
        logger.write_order(to_process[0], STATUS_NO_ACTION)
        print(f"  ✓ Updated CSV: status=no_action_needed")
        
        # Order 2: Payment canceled successfully
        print(f"\nProcessing order {to_process[1]}...")
        print("  → Checking Papaya database...")
        time.sleep(0.3)
        print("  → Found payment ID: 98765")
        print("  → Calling Papaya API to cancel payment...")
        time.sleep(0.5)
        print("  → API response: 200 OK")
        logger.write_order(to_process[1], STATUS_SUCCESS, payment_id='98765')
        print(f"  ✓ Updated CSV: status=payment_canceled_success, payment_id=98765")
        
        # Order 3: Payment cancellation failed
        print(f"\nProcessing order {to_process[2]}...")
        print("  → Checking Papaya database...")
        time.sleep(0.3)
        print("  → Found payment ID: 98766")
        print("  → Calling Papaya API to cancel payment...")
        time.sleep(0.5)
        print("  → API response: 500 Internal Server Error")
        logger.write_order(to_process[2], STATUS_ERROR, 
                          payment_id='98766', 
                          error_message='API returned 500: Internal Server Error')
        print(f"  ✓ Updated CSV: status=payment_canceled_error")
        
        # Show final CSV content
        print("\n" + "=" * 70)
        print("Final CSV Content:")
        print("=" * 70)
        with open(csv_file, 'r') as f:
            print(f.read())
        
    finally:
        if os.path.exists(csv_file):
            os.unlink(csv_file)


def demo_resume_after_interrupt():
    """Demonstrate resuming after interruption"""
    print("\n" + "=" * 70)
    print("DEMO: Resume After Interruption")
    print("=" * 70)
    
    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
        csv_file = tmp.name
    
    try:
        os.unlink(csv_file)
        logger = CSVProgressLogger(csv_file)
        
        # Simulate first run (interrupted)
        print("\n--- First Run (Interrupted) ---")
        all_orders = ['100001234', '100001235', '100001236', '100001237', '100001238']
        
        print(f"Fetched {len(all_orders)} orders from Magento")
        logger.bulk_write_orders(all_orders, STATUS_FETCHED)
        
        # Process only first 2 orders
        print("\nProcessing orders...")
        logger.write_order('100001234', STATUS_SUCCESS, payment_id='98765')
        print(f"✓ Processed order 100001234")
        
        logger.write_order('100001235', STATUS_NO_ACTION)
        print(f"✓ Processed order 100001235")
        
        print("\n⚠️  Script interrupted (Ctrl+C) ⚠️")
        print("Remaining orders: 100001236, 100001237, 100001238")
        
        # Simulate second run (resume)
        print("\n--- Second Run (Resume) ---")
        print(f"Fetched {len(all_orders)} orders from Magento (same as before)")
        logger.bulk_write_orders(all_orders, STATUS_FETCHED)  # Won't overwrite existing
        
        # Filter already processed
        to_process = logger.get_orders_to_process(all_orders)
        print(f"\nFiltering orders...")
        print(f"  → Already processed: 2 orders")
        print(f"  → To process: {len(to_process)} orders")
        print(f"  → Orders to process: {to_process}")
        
        # Process remaining orders
        print("\nProcessing remaining orders...")
        logger.write_order('100001236', STATUS_SUCCESS, payment_id='98766')
        print(f"✓ Processed order 100001236")
        
        logger.write_order('100001237', STATUS_ERROR, payment_id='98767', 
                          error_message='Timeout')
        print(f"✓ Processed order 100001237")
        
        logger.write_order('100001238', STATUS_NO_ACTION)
        print(f"✓ Processed order 100001238")
        
        print("\n✓ All orders processed successfully!")
        
        # Show final CSV content
        print("\n" + "=" * 70)
        print("Final CSV Content:")
        print("=" * 70)
        with open(csv_file, 'r') as f:
            print(f.read())
        
    finally:
        if os.path.exists(csv_file):
            os.unlink(csv_file)


def demo_error_recovery():
    """Demonstrate error recovery"""
    print("\n" + "=" * 70)
    print("DEMO: Error Recovery")
    print("=" * 70)
    
    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
        csv_file = tmp.name
    
    try:
        os.unlink(csv_file)
        logger = CSVProgressLogger(csv_file)
        
        print("\nProcessing orders with various outcomes...")
        
        # Success
        logger.write_order('100001234', STATUS_SUCCESS, payment_id='98765')
        print("✓ Order 100001234: Payment canceled successfully")
        
        # Error with detailed message
        logger.write_order('100001235', STATUS_ERROR, 
                          payment_id='98766',
                          error_message='Connection timeout after 30 seconds')
        print("✗ Order 100001235: Failed - Connection timeout")
        
        # No action needed
        logger.write_order('100001236', STATUS_NO_ACTION)
        print("○ Order 100001236: No action needed")
        
        # Another error
        logger.write_order('100001237', STATUS_ERROR,
                          payment_id='98767',
                          error_message='API returned 403: Forbidden - Invalid API key')
        print("✗ Order 100001237: Failed - Invalid API key")
        
        # Show CSV with errors
        print("\n" + "=" * 70)
        print("CSV Content (with errors):")
        print("=" * 70)
        with open(csv_file, 'r') as f:
            content = f.read()
            print(content)
        
        print("\n📊 Summary:")
        print("  → 1 success")
        print("  → 2 errors (can be retried or investigated)")
        print("  → 1 no action needed")
        
    finally:
        if os.path.exists(csv_file):
            os.unlink(csv_file)


def main():
    """Run all demos"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "CSV Progress Logger - Demonstrations" + " " * 17 + "║")
    print("╚" + "═" * 68 + "╝")
    
    try:
        demo_basic_flow()
        input("\n\nPress Enter to continue to next demo...")
        
        demo_resume_after_interrupt()
        input("\n\nPress Enter to continue to next demo...")
        
        demo_error_recovery()
        
        print("\n\n" + "=" * 70)
        print("All demos completed successfully!")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(1)


if __name__ == '__main__':
    main()
