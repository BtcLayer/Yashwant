import sys
import os

# Set up path
sys.path.insert(0, os.getcwd())
# os.chdir(os.getcwd())

try:
    print("Starting 24h bot...")
    from live_demo_24h import main
    import asyncio
    asyncio.run(main.run_live('live_demo_24h/config.json'))
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    input("\nPress Enter to close...")
