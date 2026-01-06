import sys
import os

# Set up path
sys.path.insert(0, os.getcwd())
# os.chdir(os.getcwd()) # Already in cwd

try:
    print("Starting bot...")
    # Import and run main
    from live_demo import main
    import asyncio
    asyncio.run(main.run_live('live_demo/config.json'))
except Exception as e:
    print(f"\nERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    input("\nPress Enter to close...")
