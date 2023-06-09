'''Easy context-based profiling with logging support'''

from __future__ import annotations

__version__ = '0.1.3'

__all__ = (
    'BaseProfile',
    'LogProfile',
    'ignore',
    'ignored',
    'log',
    'profile',
)

import tracemalloc
from datetime import timedelta
from sys import getprofile, setprofile
from time import perf_counter
from types import FrameType
from typing import Any, Callable

ProfileType = Callable[[FrameType, str, Any], Any]

PROFILE_IGNORE = set()


def fnb(n: int) -> str:
    '''Format number of bytes as a human-readable string.'''
    x = float(n)
    for u in ['B', 'K', 'M', 'G', 'T', 'P']:
        if x < 1000:
            break
        x /= 1000
    return f'{x:.3f}'[:5] + u


def fname(frame):
    '''Return the function name from a frame.'''
    name = frame.f_code.co_name
    try:
        qualname = frame.f_code.co_qualname
    except AttributeError:
        qualname = name
    if qualname.endswith(name):
        name = qualname
    return name


def cname(func):
    '''Return the function name from a C function.'''
    name = func.__name__
    try:
        qualname = func.__qualname__
    except AttributeError:
        qualname = name
    if qualname.endswith(name):
        name = qualname
    return name


def ignored(func):
    '''Mark a function as ignored by the profiler.'''
    PROFILE_IGNORE.add(func.__code__)
    return func


class profile:
    '''Context manager for scoped profiling.'''

    def __init__(self, func: ProfileType) -> None:
        self.func = func
        self.stack: list[ProfileType | None] = []

    @ignored
    def __enter__(self) -> None:
        func = self.func

        if func is not None:
            target = self.__enter__.__code__

            def trap(frame: FrameType, event: str, arg: Any) -> None:
                if event == 'return' and frame.f_code == target:
                    scope = frame.f_back

                    def prof(frame: FrameType, event: str, arg: Any) -> None:
                        if event == 'c_call' or event == 'c_return':
                            in_scope = frame is scope
                        else:
                            in_scope = frame.f_back is scope

                        if in_scope and frame.f_code not in PROFILE_IGNORE:
                            func(frame, event, arg)

                    setprofile(prof)
        else:
            trap = None

        self.stack.append(getprofile())
        setprofile(trap)
        return func

    @ignored
    def __exit__(self, *args: Any) -> None:
        setprofile(self.stack.pop())


ignore = profile(None)


class BaseProfile:

    @classmethod
    def profile(cls, *args: Any, **kwargs: Any) -> profile:
        return profile(cls(*args, **kwargs))

    def __call__(self, frame: FrameType, event: str, arg: Any) -> None:
        handler = getattr(self, f'_{event}', None)
        if handler is not None:
            handler(frame, arg)


class LogProfile(BaseProfile):

    def __init__(self, log: Callable[[str], Any]) -> None:
        self.log = log
        self.counts: dict[int, float] = {}

    def __start(self, obj: Any) -> None:
        self.counts[hash(obj)] = perf_counter()

    def __stop(self, obj: Any) -> float:
        count = perf_counter()
        return count - self.counts.pop(hash(obj), count)

    def __log(self, time: float, name: str) -> None:
        parr = []
        if time > 0:
            parr += [f'{timedelta(seconds=time)!s}']
        if tracemalloc.is_tracing():
            mem, peak = tracemalloc.get_traced_memory()
            parr += [f'{fnb(mem)}', f'{fnb(peak)}']
        if parr:
            prof = '[' + ' - '.join(parr) + ']'
        else:
            prof = ''
        self.log(f'{prof} {name}')

    def _call(self, frame: FrameType, arg: Any) -> None:
        self.__start(frame)

    def _return(self, frame: FrameType, arg: Any) -> None:
        self.__log(self.__stop(frame), fname(frame))

    def _c_call(self, frame: FrameType, arg: Any) -> None:
        self.__start(arg)

    def _c_return(self, frame: FrameType, arg: Any) -> None:
        self.__log(self.__stop(arg), cname(arg))


log = LogProfile.profile
