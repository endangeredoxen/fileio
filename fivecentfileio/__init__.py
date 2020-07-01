import os

__author__    = 'Steve Nicholes'
__copyright__ = 'Copyright (C) 2017 Steve Nicholes'
__license__   = 'GPLv3'
with open(os.path.join(os.path.dirname(__file__), r'version.txt'), 'r') as input:
    __version__ = input.readlines()[0]
__url__       = 'https://github.com/endangeredoxen/fivecentfileio'

from . config import ConfigFile
from . html import Dir2HTML
from . reader import FileReader
from . utilities import *
