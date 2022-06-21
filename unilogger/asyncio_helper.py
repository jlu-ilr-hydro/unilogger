import asyncio
import typing

async def waitfor(coro: typing.Coroutine):
    """
    Starts a coroutine and shows some animated cursor during the waiting phase
    """
    T = asyncio.ensure_future(coro)
    while not T.done():
        for c in '-\|/':
            print(c, end='\r')
            await asyncio.sleep(0.1)
    print('done')
    return T.result()


def await_coro(coro: typing.Coroutine):
    """
    Starts a coroutine in the standard loop and animates  a cursor
    """
    return asyncio.get_event_loop().run_until_complete(waitfor(coro))
