"""Run the asynchronous ML feed worker."""

from .worker import _main

if __name__ == "__main__":
    import asyncio

    asyncio.run(_main())
