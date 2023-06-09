from unittest.mock import patch, Mock

import easyprofile


class f_inner:
    '''Test for equality of inner frames.'''
    def __init__(self, frame, depth=1):
        self.frame = frame
        self.depth = depth

    def __eq__(self, frame):
        for _ in range(self.depth):
            if frame is None:
                return False
            frame = frame.f_back
        return frame is self.frame


def test_fnb():
    assert easyprofile.fnb(0) == '0.000B'
    assert easyprofile.fnb(1) == '1.000B'
    assert easyprofile.fnb(10) == '10.00B'
    assert easyprofile.fnb(100) == '100.0B'
    assert easyprofile.fnb(1000) == '1.000K'
    assert easyprofile.fnb(1234) == '1.234K'
    assert easyprofile.fnb(12340) == '12.34K'
    assert easyprofile.fnb(123400) == '123.4K'
    assert easyprofile.fnb(1234000) == '1.234M'
    assert easyprofile.fnb(12340000) == '12.34M'
    assert easyprofile.fnb(123400000) == '123.4M'
    assert easyprofile.fnb(1234000000) == '1.234G'
    assert easyprofile.fnb(12340000000) == '12.34G'
    assert easyprofile.fnb(123400000000) == '123.4G'
    assert easyprofile.fnb(1234000000000) == '1.234T'
    assert easyprofile.fnb(12340000000000) == '12.34T'
    assert easyprofile.fnb(123400000000000) == '123.4T'
    assert easyprofile.fnb(1234000000000000) == '1.234P'
    assert easyprofile.fnb(12340000000000000) == '12.34P'
    assert easyprofile.fnb(123400000000000000) == '123.4P'


def test_ignored():
    with patch('easyprofile.PROFILE_IGNORE', set()) as s:
        assert not s

        @easyprofile.ignored
        def f():
            pass

        assert f.__code__ in s


def test_profile():
    from sys import _getframe, getprofile, setprofile

    sysp = Mock()
    prof = Mock()
    call = Mock()
    call.side_effect = Mock()

    frame = _getframe()
    setprofile(sysp)
    assert getprofile() is sysp

    call()

    with easyprofile.profile(prof):
        call()

    call()

    assert getprofile() is sysp
    setprofile(None)

    assert call.call_count == call.side_effect.call_count == 3
    assert prof.call_count == 4
    assert prof.call_args_list[0].args == (f_inner(frame), 'attach', None)
    assert prof.call_args_list[1].args == (f_inner(frame), 'call', None)
    assert prof.call_args_list[2].args == (f_inner(frame), 'return',
                                           call.side_effect.return_value)
    assert prof.call_args_list[3].args == (None, 'detach', None)


def test_ignore():
    from sys import _getframe

    prof = Mock()
    call = Mock()

    frame = _getframe()

    with easyprofile.profile(prof):
        call()
        with easyprofile.ignore:
            call()
        call()

    assert call.call_count == 3
    assert prof.call_count == 6
    assert prof.call_args_list[0].args == (f_inner(frame), 'attach', None)
    assert prof.call_args_list[1].args == (f_inner(frame), 'call', None)
    assert prof.call_args_list[2].args == (f_inner(frame), 'return',
                                           call.return_value)
    assert prof.call_args_list[3].args == (f_inner(frame), 'call', None)
    assert prof.call_args_list[4].args == (f_inner(frame), 'return',
                                           call.return_value)
    assert prof.call_args_list[5].args == (None, 'detach', None)


def test_base_profile():
    call = Mock()

    with easyprofile.BaseProfile.profile():
        call()
        call()

    assert call.call_count == 2

    class TestProfile(easyprofile.BaseProfile):
        __init__ = staticmethod(Mock(return_value=None))
        _attach = staticmethod(Mock())
        _detach = staticmethod(Mock())
        _call = staticmethod(Mock())
        _return = staticmethod(Mock())

    with TestProfile.profile(0, kw=1):
        call()
        call()

    TestProfile.__init__.assert_called_once_with(0, kw=1)
    assert TestProfile._attach.call_count == 1
    assert TestProfile._detach.call_count == 1
    assert TestProfile._call.call_count == 2
    assert TestProfile._return.call_count == 2
