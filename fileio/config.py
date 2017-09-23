############################################################################
# config.py
#
#   ini-style config file reader
#
############################################################################
__author__    = 'Steve Nicholes'
__copyright__ = 'Copyright (C) 2017 Steve Nicholes'
__license__   = 'GPLv3'
__url__       = 'https://github.com/endangeredoxen/fileio'


try:
    import configparser
except:
    import ConfigParser as configparser
import os
oswalk = os.walk
import pdb
try:
    import win32clipboard
except Exception:
    pass
from . import utilities as util
osjoin = os.path.join
st = pdb.set_trace


class ConfigFile():
    def __init__(self, path=None, paste=False, raw=False):
        """
        Config file reader

        Reads and parses a config file of the .ini format.  Data types are
        interpreted using str_2_dtype and all parameters are stored in both
        a ConfigParser class and a multi-dimensional dictionary.  "#" is the
        comment character.

        Args:
            path (str): location of the ini file (default=None)
            paste (bool): allow pasting of a config file from the clipboard

        """

        self.config_path = path
        self.config = configparser.RawConfigParser()
        self.config_dict = {}
        self.is_valid = False
        self.paste = paste
        self.raw = raw
        self.rel_path = os.path.dirname(__file__)

        if self.config_path:
            self.validate_file_path()
        if self.is_valid:
            self.read_file()
        elif self.paste:
            self.read_pasted()
        elif self.raw is not False:
            self.read_raw()
        else:
            raise ValueError('Could not find a config.ini file at the '
                             'following location: %s' % self.config_path)

        self.make_dict()

    def make_dict(self):
        """
        Convert the configparser object into a dictionary for easier handling
        """
        self.config_dict = {s:{k: util.str_2_dtype(v)
                            for k, v in self.config.items(s)}
                            for s in self.config.sections()}

    def read_file(self):
        """
        Read the config file as using the parser option
        """

        self.config.read(self.config_path)

    def read_pasted(self):
        """
        Read from clipboard
        """
        win32clipboard.OpenClipboard()
        data = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        self.config.read_string(data)

    def read_raw(self):
        """
        Read from a raw string
        """

        self.config.read_string(self.raw)

    def validate_file_path(self):
        """
        Make sure there is a valid config file at the location specified by
        self.config_path
        """

        if os.path.exists(self.config_path):
            self.is_valid = True
        else:
            if os.path.exists(osjoin(self.rel_path, file)):
                self.config_path = osjoin(self.rel_path, self.config_path)
                self.is_valid = True

