import pandas as pd
import os

# Define the path to your GADSL Excel file
GADSL_FILE_NAME = "GADSL-Reference-List.xlsx"
# Construct the absolute path relative to where this script is run
GADSL_FILE_PATH = os.path.join(os.path.dirname(__file__), GADSL_FILE_NAME)

print(f"Attempting to read Excel file from: {GADSL_FILE_PATH}")

try:
    df_temp = pd.read_excel(GADSL_FILE_PATH)
    print("\n--- EXACT EXCEL COLUMN HEADERS ---")
    print("Copy these strings EXACTLY into your df.rename dictionary keys.")
    print("-----------------------------------")
    for col in df_temp.columns:
        # Using repr() to show exact string representation, including newlines, tabs, and unicode characters
        print(f"'{repr(col)[1:-1]}'") # [1:-1] removes the outer single quotes from repr() for cleaner output
    print("-----------------------------------")
    print("\nExample: if you see 'My\\nColumn', use 'My\\nColumn' as the key.")
    print("If you see 'Column\\xa0With\\xa0Space', use 'Column\\xa0With\\xa0Space'.")

except FileNotFoundError:
    print(f"Error: GADSL file not found at {GADSL_FILE_PATH}. Make sure it's in the same directory.")
except Exception as e:
    print(f"An error occurred while reading the Excel file: {e}")