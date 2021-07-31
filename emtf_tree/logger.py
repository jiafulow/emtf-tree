# The following source code was originally obtained from:
# https://github.com/rootpy/rootpy/blob/master/rootpy/logger/__init__.py
# https://github.com/rootpy/rootpy/blob/master/rootpy/logger/formatter.py
# ==============================================================================

# Copyright (c) 2012-2017, The rootpy developers
# All rights reserved.
#
# Please refer to LICENSE.rootpy for the license terms.
# ==============================================================================
"""This module provides the default logger."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import os

# The background is set with 40 plus the number of the color, and the foreground with 30
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

COLORS = {
    'DEBUG'      : BLUE,
    'INFO'       : WHITE,
    'WARNING'    : YELLOW,
    'ERROR'      : RED,
    'CRITICAL'   : RED,
}

# These are the sequences need to get colored ouput
RESET_SEQ = '\033[0m'
COLOR_SEQ = '\033[1;%dm'
BOLD_SEQ = '\033[1m'
FORMAT = '[{color}{levelname}$RESET:$BOLD{name}$RESET] {message}'


def formatter_message(message, use_color=False):
    if use_color:
        message = message.replace('$RESET', RESET_SEQ).replace('$BOLD', BOLD_SEQ)
    else:
        message = message.replace('$RESET', '').replace('$BOLD', '')
    return message


class CustomFormatter(logging.Formatter):
    def __init__(self):
        fmt = formatter_message(FORMAT)
        super(CustomFormatter, self).__init__(fmt=fmt)

    def format(self, record):
        if not hasattr(record, 'message'):
            record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        return self._fmt.format(color='', **record.__dict__)


class CustomColoredFormatter(logging.Formatter):
    def __init__(self, use_color=True):
        fmt = formatter_message(FORMAT, use_color=use_color)
        super(CustomColoredFormatter, self).__init__(fmt=fmt)
        self.use_color = use_color

    def format(self, record):
        if self.use_color and record.levelname in COLORS:
            # add 30 to get foreground color
            record.color = COLOR_SEQ % (30 + COLORS[record.levelname])
        else:
            record.color = ''
        if not hasattr(record, 'message'):
            record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        return self._fmt.format(**record.__dict__)


log_root = logging.getLogger()
if not log_root.handlers:
    # Add a handler to the top-level logger if it doesn't already have one
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    isatty = getattr(handler.stream, 'isatty', False)
    if isatty and isatty():
        handler.setFormatter(CustomColoredFormatter())
    else:
        handler.setFormatter(CustomFormatter())
    log_root.addHandler(handler)
    # Make the top-level logger as verbose as possible.
    # Log messages that make it to the screen are controlled by the handler
    log_root.setLevel(logging.DEBUG)


def get_logger(name='user'):
    log = logging.getLogger(name)
    if not os.environ.get('DEBUG', False):
        log.setLevel(logging.INFO)
    return log


log = get_logger('tree')
