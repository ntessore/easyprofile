# `easyprofile` — Easy context-based profiling for Python

The `easyprofile` package provides facilities for setting Python's
`sys.setprofile()` locally within a context, together with a number of helpers
to automate profiling and logging.

## Installation

Install as usual with pip:

```console
pip install easyprofile
```

## Usage

### Replacing `sys.setprofile()` locally

If you wish to install a profile function that you would otherwise pass to
`sys.setprofile()` within a local context, use the `easyprofile.profile`
context manager:

```py
>>> import easyprofile
>>>
>>> # profile function of the sys.setprofile() form
>>> def myfunc(frame, event, arg):
...     print('profile:', event)
...
>>> # a test function to be profiled
>>> def profile_this(n):
...     # this inner function call will not show in the profile
...     return sum(range(n))
...
>>> # replace the profile function locally
>>> with easyprofile.profile(myfunc):
...     # only this call will be profiled
...     profile_this(100_000_000)
...
profile: call
profile: return
4999999950000000

```

### Ignoring calls

If you wish to ignore some calls locally, you can use the `easyprofile.ignore`
context manager:

```py
>>> with easyprofile.profile(myfunc):
...     # this call will be profiled
...     profile_this(100_000_000)
...
...     with easyprofile.ignore:
...         # this call will be ignored
...         profile_this(100)
...
profile: call
profile: return
4999999950000000
4950

```

The context manager works by temporarily setting `sys.setprofile()` to `None`,
and hence works with any profiler.

Note that `easyprofile.ignore` is not a callable!

### Marking functions as ignored

Functions can be marked as always ignored using the `@easyprofile.ignored`
decorator:

```py
>>> # this function is ignored by easyprofile
>>> @easyprofile.ignored
... def ignored_func():
...     return 42
...
>>> with easyprofile.profile(myfunc):
...     ignored_func()
...
42

```

Note that unlike the `easyprofile.ignore` context manager, the decorator only
works with `easyprofile`.

### Class-based profilers

To facilitate the creation of custom profilers, the `easyprofile.BaseProfile`
class provides a method-based interface to handling events.  A method
with a name `_<event>` (i.e. underscore -- event name) is called whenever the
event `<event>` is encountered, with a signature of `frame, arg`.

```py
>>> class MyProfile(easyprofile.BaseProfile):
...     def __init__(self, arg, *, kwarg):
...         print(f'MyProfile: init, {arg=}, {kwarg=}')
...
...     def _call(self, frame, arg):
...         print('MyProfile: function called')
... 
...     def _return(self, frame, arg):
...         print('MyProfile: function returned')
... 
...     # profile C extension calls using the same methods
...     _c_call = _call
...     _c_return = _return
...

```

The class-based profilers are easily invoked through their `profile()` class
method, which forwards its arguments to the constructor:

```py
>>> # use the MyProfile class for local profiling
>>> with MyProfile.profile('hello', kwarg='world'):
...     profile_this(100_000_000)
...
MyProfile: init, arg='hello', kwarg='world'
MyProfile: function called
MyProfile: function returned
4999999950000000

```
