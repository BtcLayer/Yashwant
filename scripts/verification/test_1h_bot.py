"""
Quick test of 1h bot - run for 30 seconds to verify it works
"""
import subprocess
import time
import sys

print("=" * 70)
print("Testing 1h Bot with Newly Trained Model")
print("=" * 70)
print()
print("Starting bot for 30 seconds to verify it works...")
print("Press Ctrl+C to stop early if you see it's working")
print()

try:
    # Start the bot
    process = subprocess.Popen(
        ['python', 'run_1h.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Monitor output for 30 seconds
    start_time = time.time()
    timeout = 30
    
    print("Bot output:")
    print("-" * 70)
    
    while time.time() - start_time < timeout:
        # Check if process is still running
        if process.poll() is not None:
            print("\n⚠️ Bot stopped unexpectedly!")
            stdout, stderr = process.communicate()
            if stderr:
                print("Error output:")
                print(stderr)
            break
        
        # Read output line by line
        line = process.stdout.readline()
        if line:
            print(line.strip())
        
        time.sleep(0.1)
    
    # Stop the bot
    if process.poll() is None:
        print()
        print("-" * 70)
        print("✅ Bot ran successfully for 30 seconds!")
        print("Stopping bot...")
        process.terminate()
        time.sleep(2)
        if process.poll() is None:
            process.kill()
    
    print()
    print("=" * 70)
    print("Test complete!")
    print("=" * 70)
    
except KeyboardInterrupt:
    print("\n\nStopping bot...")
    if process.poll() is None:
        process.terminate()
    print("✅ Test stopped by user")
except Exception as e:
    print(f"❌ Error: {e}")
    if 'process' in locals() and process.poll() is None:
        process.terminate()
