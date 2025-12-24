"""
Test Hyperliquid WebSocket Connection
Verifies correct subscription format and message reception
"""
import asyncio
import aiohttp
import json
from datetime import datetime

async def test_hyperliquid_ws():
    print("=" * 70)
    print("HYPERLIQUID WEBSOCKET DIAGNOSTIC TEST")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    ws_url = "wss://api.hyperliquid.xyz/ws"
    coin = "BTC"
    test_duration = 30  # seconds
    
    try:
        print(f"[1/4] Connecting to: {ws_url}")
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url, timeout=10) as ws:
                print(f"✅ Connected successfully at {datetime.now().strftime('%H:%M:%S')}")
                print()
                
                # CORRECT subscription format from official Hyperliquid docs
                subscription = {
                    "method": "subscribe",
                    "subscription": {
                        "type": "trades",
                        "coin": coin
                    }
                }
                
                print(f"[2/4] Sending subscription:")
                print(f"      {json.dumps(subscription, indent=6)}")
                await ws.send_json(subscription)
                print(f"✅ Subscription sent at {datetime.now().strftime('%H:%M:%S')}")
                print()
                
                print(f"[3/4] Listening for messages (max {test_duration} seconds)...")
                print("-" * 70)
                
                start_time = asyncio.get_event_loop().time()
                msg_count = 0
                subscription_acked = False
                trade_count = 0
                
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        msg_count += 1
                        
                        try:
                            data = json.loads(msg.data)
                            
                            # Check for subscription acknowledgment
                            if data.get("channel") == "subscriptionResponse":
                                subscription_acked = True
                                print(f"\n✅ SUBSCRIPTION ACKNOWLEDGED:")
                                print(f"   {json.dumps(data, indent=3)}")
                                print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
                                print("-" * 70)
                            
                            # Check for trade messages
                            elif data.get("channel") == "trades":
                                trade_count += 1
                                trades = data.get("data", [])
                                
                                if trade_count == 1:
                                    print(f"\n✅ FIRST TRADE MESSAGE RECEIVED:")
                                    print(f"   Trades count: {len(trades)}")
                                    if trades:
                                        sample = trades[0]
                                        print(f"   Sample trade:")
                                        print(f"     - coin: {sample.get('coin')}")
                                        print(f"     - side: {sample.get('side')}")
                                        print(f"     - price: {sample.get('px')}")
                                        print(f"     - size: {sample.get('sz')}")
                                        print(f"     - time: {sample.get('time')}")
                                    print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
                                    print("-" * 70)
                                elif trade_count % 10 == 0:
                                    print(f"   [{trade_count}] Received {len(trades)} trades at {datetime.now().strftime('%H:%M:%S')}")
                            
                            # Unknown message type
                            else:
                                if msg_count <= 5:  # Only show first few unknown messages
                                    print(f"\n⚠️  UNKNOWN MESSAGE TYPE:")
                                    print(f"   {json.dumps(data, indent=3)[:300]}")
                                    print("-" * 70)
                        
                        except json.JSONDecodeError:
                            print(f"\n❌ Failed to parse message: {msg.data[:100]}")
                    
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f"\n❌ WebSocket error: {msg.data}")
                        break
                    
                    # Check timeout
                    if asyncio.get_event_loop().time() - start_time > test_duration:
                        print(f"\n⏱️  Test duration reached ({test_duration}s)")
                        break
                
                print("\n" + "=" * 70)
                print("[4/4] TEST RESULTS:")
                print("=" * 70)
                print(f"Total messages received: {msg_count}")
                print(f"Subscription acknowledged: {'✅ YES' if subscription_acked else '❌ NO'}")
                print(f"Trade messages received: {trade_count}")
                print()
                
                if subscription_acked and trade_count > 0:
                    print("✅ SUCCESS: WebSocket is working correctly!")
                    print("   - Subscription format is correct")
                    print("   - Trade messages are being received")
                    print("   - This format should work in hyperliquid_listener.py")
                elif subscription_acked and trade_count == 0:
                    print("⚠️  PARTIAL SUCCESS: Subscription acknowledged but no trades yet")
                    print("   - Wait longer or try during active trading hours")
                elif not subscription_acked:
                    print("❌ FAILED: Subscription not acknowledged")
                    print("   - Check if subscription format is correct")
                    print("   - Check Hyperliquid API status")
                else:
                    print(f"❌ FAILED: Unexpected state (msg_count={msg_count})")
                
                print()
                print(f"Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 70)
                
    except aiohttp.ClientError as e:
        print(f"\n❌ CONNECTION ERROR: {type(e).__name__}: {e}")
        print("   - Check internet connection")
        print("   - Verify WebSocket URL is correct")
        print("   - Check if Hyperliquid API is accessible")
    except asyncio.TimeoutError:
        print(f"\n❌ TIMEOUT ERROR: Could not connect within 10 seconds")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\nStarting Hyperliquid WebSocket test...")
    print("Press Ctrl+C to stop early\n")
    
    try:
        asyncio.run(test_hyperliquid_ws())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    
    print("\nTest script completed.")
