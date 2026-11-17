import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Coroutine


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """
    Safely executes an asynchronous coroutine from a synchronous caller (such as Streamlit),
    avoiding 'Event loop is closed' or 'This event loop is already running' errors across
    thread lifecycles.
    """
    try:
        # Check if current thread has an active, running event loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # If already inside a running event loop (e.g., Streamlit internal async thread),
        # run the coroutine in a dedicated worker thread with its own clean loop.
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: asyncio.run(coro)).result()
    else:
        # No loop is currently running on this thread
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(coro)
        finally:
            try:
                # Cancel any leftover background tasks created on this loop
                pending = asyncio.all_tasks(new_loop)
                for task in pending:
                    task.cancel()
                if pending:
                    new_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            new_loop.close()
