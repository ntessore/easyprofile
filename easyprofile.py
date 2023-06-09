'''Easy context-based profiling with logging support'''

from __future__ import annotations

__version__ = '0.1.0'

__all__ = (
    'BaseProfile',
    'LogProfile',
    'ignore',
    'ignored',
    'log',
    'profile',
)

import tracemalloc
from sys import getprofile, setprofile
from datetime import timedelta
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
                    func(scope, 'attach', None)
        else:
            trap = None

        self.stack.append(getprofile())
        setprofile(trap)
        return func

    @ignored
    def __exit__(self, *args: Any) -> None:
        if self.func is not None:
            self.func(None, 'detach', None)
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
        self.counts: dict[FrameType, float] = {}
        self.frame: FrameType | None = None

    def _attach(self, frame: FrameType, arg: Any) -> None:
        self.frame = frame

    def _detach(self, frame: FrameType, arg: Any) -> None:
        self.frame = None

    def _call(self, frame: FrameType, arg: Any) -> None:
        self.counts[frame] = perf_counter()

    def _return(self, frame: FrameType, arg: Any) -> None:
        count = perf_counter()
        delta = count - self.counts.get(frame, count)

        names = []
        f: FrameType | None = frame
        while f:
            name = f.f_code.co_name
            try:
                qualname = f.f_code.co_qualname
            except AttributeError:
                qualname = name
            if qualname.endswith(name):
                name = qualname
            names.append(name)
            if f == self.frame:
                break
            f = f.f_back
        name = ' > '.join(names[-2::-1])

        parr = []
        if delta > 0:
            parr += [f'{timedelta(seconds=delta)!s}']
        if tracemalloc.is_tracing():
            mem, peak = tracemalloc.get_traced_memory()
            parr += [f'{fnb(mem)}', f'{fnb(peak)}']

        if parr:
            prof = '[' + ' - '.join(parr) + ']'
        else:
            prof = ''

        self.log(f'{prof} {name}')

    _c_call = _call
    _c_return = _return


log = LogProfile.profile
