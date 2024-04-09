# -*- encoding: utf-8 -*-
# merge_args v0.1.5
# Merge signatures of two functions with Advanced Hackery.
# Copyright © 2018-2023, Chris Warrick.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions, and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions, and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the author of this software nor the names of
#    contributors to this software may be used to endorse or promote
#    products derived from this software without specific prior written
#    consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Merge signatures of two functions with Advanced Hackery. Useful for wrappers.

Usage: @merge_args(old_function)
"""

import inspect
import itertools
import types
import functools
import sys
import typing

__version__ = '0.1.5'
__all__ = ('merge_args',)


PY38 = sys.version_info >= (3, 8)
PY310 = sys.version_info >= (3, 10)
PY311 = sys.version_info >= (3, 11)


def _blank():  # pragma: no cover
    pass


def _merge(
    source,
    dest,
    drop_args: typing.Optional[typing.List[str]] = None,
    drop_kwonlyargs: typing.Optional[typing.List[str]] = None,
):
    """Merge the signatures of ``source`` and ``dest``.

    ``dest`` args go before ``source`` args in all three categories
    (positional, keyword-maybe, keyword-only).
    """
    if drop_args is None:
        drop_args = []
    if drop_kwonlyargs is None:
        drop_kwonlyargs = []
    source_spec = inspect.getfullargspec(source)
    dest_spec = inspect.getfullargspec(dest)

    if source_spec.varargs or source_spec.varkw:
        return dest

    source_all = source_spec.args
    dest_all = dest_spec.args

    if source_spec.defaults:
        source_pos = source_all[:-len(source_spec.defaults)]
        source_kw = source_all[-len(source_spec.defaults):]
    else:
        source_pos = source_all
        source_kw = []

    if dest_spec.defaults:
        dest_pos = dest_all[:-len(dest_spec.defaults)]
        dest_kw = dest_all[-len(dest_spec.defaults):]
    else:
        dest_pos = dest_all
        dest_kw = []

    args_merged = dest_pos
    for a in source_pos:
        if a not in args_merged and a not in drop_args:
            args_merged.append(a)

    defaults_merged = []
    for a, default in itertools.chain(
        zip(dest_kw, dest_spec.defaults or []),
        zip(source_kw, source_spec.defaults or [])
    ):
        if a not in args_merged and a not in drop_args:
            args_merged.append(a)
            defaults_merged.append(default)

    kwonlyargs_merged = dest_spec.kwonlyargs
    for a in source_spec.kwonlyargs:
        if a not in kwonlyargs_merged and a not in drop_kwonlyargs:
            kwonlyargs_merged.append(a)

    args_all = tuple(args_merged + kwonlyargs_merged)

    if PY38:
        replace_kwargs = {
            'co_argcount': len(args_merged),
            'co_kwonlyargcount': len(kwonlyargs_merged),
            'co_posonlyargcount': dest.__code__.co_posonlyargcount,
            'co_nlocals': len(args_all),
            'co_flags': source.__code__.co_flags,
            'co_varnames': args_all,
            'co_filename': dest.__code__.co_filename,
            'co_name': dest.__code__.co_name,
            'co_firstlineno': dest.__code__.co_firstlineno,
        }

        if PY310:
            replace_kwargs['co_linetable'] = dest.__code__.co_linetable
        else:
            replace_kwargs['co_lnotab'] = dest.__code__.co_lnotab

        if PY311:
            replace_kwargs['co_exceptiontable'] = dest.__code__.co_exceptiontable
            replace_kwargs['co_qualname'] = dest.__code__.co_qualname

        passer_code = _blank.__code__.replace(**replace_kwargs)
    else:
        passer_args = [
            len(args_merged),
            len(kwonlyargs_merged),
            _blank.__code__.co_nlocals,
            _blank.__code__.co_stacksize,
            source.__code__.co_flags,
            _blank.__code__.co_code, (), (),
            args_all, dest.__code__.co_filename,
            dest.__code__.co_name,
            dest.__code__.co_firstlineno,
            dest.__code__.co_lnotab,
        ]
        passer_code = types.CodeType(*passer_args)

    passer = types.FunctionType(passer_code, globals())
    dest.__wrapped__ = passer

    # annotations

    # ensure we take destination’s return annotation
    has_dest_ret = 'return' in dest.__annotations__
    if has_dest_ret:
        dest_ret = dest.__annotations__['return']

    for v in ('__kwdefaults__', '__annotations__'):
        out = getattr(source, v)
        if out is None:
            out = {}
        if getattr(dest, v) is not None:
            out = out.copy()
            out.update(getattr(dest, v))
            setattr(passer, v, out)

    if has_dest_ret:
        passer.__annotations__['return'] = dest_ret
    dest.__annotations__ = passer.__annotations__

    passer.__defaults__ = tuple(defaults_merged)
    if not dest.__doc__:
        dest.__doc__ = source.__doc__
    return dest


def merge_args(
    source,
    drop_args: typing.Optional[typing.List[str]] = None,
    drop_kwonlyargs: typing.Optional[typing.List[str]] = None,
):
    """Merge the signatures of two functions."""
    try:
        return functools.partial(
            lambda x, y: _merge(x, y, drop_args, drop_kwonlyargs), source
        )
    except TypeError:
        pass
