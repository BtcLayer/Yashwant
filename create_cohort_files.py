"""
Step 1: Create cohort CSV files from existing assets
"""
import pandas as pd
import os

print("=" * 80)
print("CREATING COHORT FILES")
print("=" * 80)

# Read existing cohort files
print("\n1. Loading existing cohort data from assets/...")
extremely_prof = pd.read_csv('live_demo/assets/extremely_profitable_cohort.csv')
very_prof = pd.read_csv('live_demo/assets/very_profitable_cohort.csv')
rekt = pd.read_csv('live_demo/assets/rekt_cohort.csv')
very_unprof = pd.read_csv('live_demo/assets/very_unprofitable_cohort.csv')

print(f"   Extremely profitable: {len(extremely_prof)} addresses")
print(f"   Very profitable: {len(very_prof)} addresses")
print(f"   Rekt: {len(rekt)} addresses")
print(f"   Very unprofitable: {len(very_unprof)} addresses")

# Create top cohort (combine extremely and very profitable)
print("\n2. Creating top_cohort.csv (profitable traders)...")
top_cohort = pd.concat([extremely_prof, very_prof], ignore_index=True)
top_cohort = top_cohort.drop_duplicates()
print(f"   Total top traders: {len(top_cohort)}")

# Create bottom cohort (combine rekt and very unprofitable)
print("\n3. Creating bottom_cohort.csv (unprofitable traders)...")
bottom_cohort = pd.concat([rekt, very_unprof], ignore_index=True)
bottom_cohort = bottom_cohort.drop_duplicates()
print(f"   Total bottom traders: {len(bottom_cohort)}")

# Save to expected locations
top_path = 'live_demo/top_cohort.csv'
bottom_path = 'live_demo/bottom_cohort.csv'

top_cohort.to_csv(top_path, index=False)
bottom_cohort.to_csv(bottom_path, index=False)

print(f"\n4. Files created:")
print(f"   {top_path} ({os.path.getsize(top_path)} bytes)")
print(f"   {bottom_path} ({os.path.getsize(bottom_path)} bytes)")

print("\nSUCCESS: Cohort files created!")
print("=" * 80)
