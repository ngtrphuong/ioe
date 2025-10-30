#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mock Data Generation Script
Uses Django management command generate_sample_data to create test data
"""

import os
import sys
import subprocess

def main():
    """
    Use Django management command to generate sample data
    """
    print("Calling Django management command to generate sample data...")
    
    try:
        # Set environment variable for UTF-8 encoding
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # Use subprocess to call Django management command
        cmd = [sys.executable, "manage.py", "generate_sample_data", 
               "--products", "100", 
               "--members", "50", 
               "--sales", "200", 
               "--clean"]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env, encoding='utf-8')
        print(result.stdout)
        
        print("Sample data generation completed!")
        print("You can adjust parameters using the following command to generate different amounts of data:")
        print("python manage.py generate_sample_data --products <number> --members <number> --sales <number> --clean")
        
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while generating sample data: {e}")
        print(f"Error message: {e.stderr}")
    except Exception as e:
        print(f"Unknown error occurred: {e}")

if __name__ == "__main__":
    main() 