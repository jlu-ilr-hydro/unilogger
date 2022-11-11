import asyncio
import typing
import time

async def waitfor(coro: typing.Coroutine):
    """
    Starts a coroutine and shows some animated cursor during the waiting phase
    """
    T = asyncio.ensure_future(coro)
    t_start = time.time()
    while not T.done():
        for c in '-\|/':
            print(c, end='\r')
            await asyncio.sleep(0.1)
    print('done after {:0.2}s'.format(time.time() -t_start))
    return T.result()


def await_coro(coro: typing.Coroutine):
    """
    Starts a coroutine in the standard loop and animates  a cursor
    """
    return asyncio.get_event_loop().run_until_complete(waitfor(coro))
