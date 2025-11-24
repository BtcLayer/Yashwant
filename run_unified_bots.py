#!/usr/bin/env python3
"""
Unified Trading Bot Runner
Runs all four versions (5min, 1h, 12h, 24h) simultaneously in one container
"""

import asyncio
import os
import sys


async def run_all_bots():
    """Run all trading bot versions concurrently"""
    # Import all versions
    from live_demo.main import run_live as run_5min
    from live_demo_1h.main import run_live as run_1h
    from live_demo_12h.main import run_live as run_12h
    from live_demo_24h.main import run_live as run_24h

    print("Starting MetaStackerBandit - All 4 Versions")
    print("=" * 50)
    print("5-minute version: live_demo/config.json")
    print("1-hour version:   live_demo_1h/config.json")
    print("12-hour version:  live_demo_12h/config.json")
    print("24-hour version:  live_demo_24h/config.json")
    print()

    # Dry-run control: respect env var DRY_RUN ("true"/"false").
    # Default to True for safety if not provided.
    dr_env = os.environ.get('DRY_RUN', '').strip().lower()
    if dr_env in ('false', '0', 'no', 'off'):
        dry_run = False
    elif dr_env in ('true', '1', 'yes', 'on'):
        dry_run = True
    else:
        dry_run = True

    # Create tasks for all versions with per-task exception logging
    tasks = []

    async def _run_with_guard(name: str, coro):
        log_path = os.path.join(os.path.dirname(__file__), 'paper_trading_outputs', f'unified_runner_{name}.log')
        try:
            await coro
        except Exception as e:  # noqa: BLE001
            # Log exception to per-task log and stderr, then re-raise to stop gather()
            try:
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                import traceback
                with open(log_path, 'a', encoding='utf-8') as fh:
                    fh.write('\n===== Uncaught exception in task: ' + name + ' =====\n')
                    fh.write('Type: ' + type(e).__name__ + '\n')
                    fh.write('Message: ' + str(e) + '\n')
                    fh.write(traceback.format_exc() + '\n')
            except OSError:
                pass
            print(f"[{name}] crashed: {type(e).__name__}: {e}")
            raise

    base_dir = os.path.dirname(__file__)
    cfg_5m = os.path.join(base_dir, 'live_demo', 'config.json')
    cfg_1h = os.path.join(base_dir, 'live_demo_1h', 'config.json')
    cfg_12h = os.path.join(base_dir, 'live_demo_12h', 'config.json')
    cfg_24h = os.path.join(base_dir, 'live_demo_24h', 'config.json')

    # Determine offline + one-shot flags (environment-wide)
    offline = bool(os.environ.get('LIVE_DEMO_OFFLINE'))
    one_shot = bool(os.environ.get('LIVE_DEMO_ONE_SHOT'))

    # 5-minute version
    task_5min = asyncio.create_task(_run_with_guard('5m', run_5min(cfg_5m, dry_run=dry_run)))
    tasks.append(('5m', task_5min))

    # 1-hour version
    task_1h = asyncio.create_task(_run_with_guard('1h', run_1h(cfg_1h, dry_run=dry_run)))
    tasks.append(('1h', task_1h))

    # 12-hour version
    task_12h = asyncio.create_task(_run_with_guard('12h', run_12h(cfg_12h, dry_run=dry_run)))
    tasks.append(('12h', task_12h))

    # 24-hour version
    task_24h = asyncio.create_task(_run_with_guard('24h', run_24h(cfg_24h, dry_run=dry_run)))
    tasks.append(('24h', task_24h))

    print('All versions started concurrently!')
    print(f"Dry-run mode: {dry_run} (override with DRY_RUN env)")
    print(f"Offline mode: {offline} (LIVE_DEMO_OFFLINE)")
    print(f"One-shot: {one_shot} (LIVE_DEMO_ONE_SHOT)")
    print('Press Ctrl+C to stop all versions (non one-shot)')
    print()
    try:
        # Wait for all tasks (they run forever in normal mode). If any crashes, bubble up.
        await asyncio.gather(*[task for _, task in tasks])
    except KeyboardInterrupt:
        print("\nStopping all trading bots...")
        for name, task in tasks:
            task.cancel()
        print("All versions stopped")
    except Exception as e:
        print(f"\n❌ Unexpected error in unified runner: {e}")
        print("One or more bots may have failed. Checking individual bots...")
        for name, task in tasks:
            if not task.done():
                print(f"  ✅ {name} bot: Still running")
            else:
                try:
                    result = task.result()
                    print(f"  ⚠️ {name} bot: Completed with result: {result}")
                except Exception as exc:
                    print(f"  ❌ {name} bot: Failed with error: {exc}")
        print("\n🔄 Restarting failed bots...")
        restarted = []
        for name, task in tasks:
            if task.done():
                try:
                    if name == '5m':
                        new_task = asyncio.create_task(_run_with_guard('5m', run_5min(cfg_5m, dry_run=dry_run)))
                    elif name == '1h':
                        new_task = asyncio.create_task(_run_with_guard('1h', run_1h(cfg_1h, dry_run=dry_run)))
                    elif name == '12h':
                        new_task = asyncio.create_task(_run_with_guard('12h', run_12h(cfg_12h, dry_run=dry_run)))
                    elif name == '24h':
                        new_task = asyncio.create_task(_run_with_guard('24h', run_24h(cfg_24h, dry_run=dry_run)))
                    restarted.append((name, new_task))
                    print(f"  ✅ {name} bot: Restarted")
                except Exception as restart_exc:
                    print(f"  ❌ {name} bot: Failed to restart: {restart_exc}")
        tasks.extend(restarted)
        remaining_tasks = [(n, t) for n, t in tasks if not t.done()]
        if remaining_tasks:
            print("\n✅ Continuing with remaining bots...")
            await asyncio.gather(*[t for _, t in remaining_tasks], return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(run_all_bots())
