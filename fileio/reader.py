############################################################################
# reader.py
#
#   Base file reader class
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
import re
import os
oswalk = os.walk
import pandas as pd
import pdb
import sys
import textwrap
try:
    import win32clipboard
except Exception:
    pass
from . import utilities as util
osjoin = os.path.join
st = pdb.set_trace


class FileReader():
    def __init__(self, path, **kwargs):
        """
        Reads multiple raw data files into memory based on a partial path name
        or a list of files and populates them into a single pandas DataFrame
        or a list of DataFrames

        Args:
            path (str|list): partial path name or list of files

        Keyword Args:
            contains (str|list): search string(s) used to filter the file
                list; default=''
            concat (bool):  True=concatenate all DataFrames into one |
                False=return a list of DataFrames; default=True
            exact (bool): uses exact matching in filenames if True else regex
            gui (bool):  True=use a PyQt4 gui prompt to select files |
                False=search directories automatically; default=False
            labels (list|str): adds a special label column to the DataFrame
                for distinguishing between files
                list=one entry per DataFrame added in order of self.file_list
                str=single label added to all files (ex. today's date,
                username, etc.)
            meta2df (bool): if True convert meta to concatenated DataFrame
            read (bool): read the DataFrames after compiling the file_list
            scan (bool): search subdirectories
            split_char (str|list): chars by which to split the filename
            split_values (list): values to extract from the filename based on
                file_split (ex. Filename='MyData_20151225_Wfr16.txt' -->
                file_split = '_' and split_values = [None, 'Date', 'Wafer']
            skip_initial_space (bool):  remove leading whitespace from
                split_values
            tag_char (str): split character for file tag values
                (ex. Filename='MyData_T=25C.txt' --> removes T= and adds 25C
                to a column named T
            verbose (bool): print file read progress

        """

        self.path = path
        self.contains = kwargs.get('contains', '')
        self.contains_OR = kwargs.get('contains_OR', [])
        self.exact = kwargs.get('exact', True)
        self.header = kwargs.get('header', True)
        self.concat = kwargs.get('concat', True)
        self.exclude = kwargs.get('exclude', [])
        self.ext = kwargs.get('ext', '')
        self.gui = kwargs.get('gui', False)
        self.labels = kwargs.get('labels', [])
        self.meta2df = kwargs.get('meta2df', True)
        self.scan = kwargs.get('scan', False)
        self.read = kwargs.get('read', True)
        self.include_filename = kwargs.get('include_filename', True)
        self.split_char = kwargs.get('split_char', ['_'])
        self.split_values = kwargs.get('split_values', [])
        self.skip_initial_space = kwargs.get('skip_initial_space', True)
        self.tag_char = kwargs.get('tag_char', '=')
        self.file_df = None
        self.file_list = []
        self.verbose = kwargs.get('verbose', True)
        self.read_func = kwargs.get('read_func', util.read_csv)
        self.counter = kwargs.get('counter', True)
        self.kwargs = kwargs

        # Format the contains value
        if type(self.contains) is not list:
            self.contains = [self.contains]

        # Format the contains_OR value
        if type(self.contains_OR) is not list:
            self.contains_OR = [self.contains_OR]

        # Format the exclude values
        if type(self.exclude) is not list:
            self.exclude = [self.exclude]

       # Format ext
        if self.ext != '':
            if type(self.ext) is not list:
                self.ext = [self.ext]
            for i, ext in enumerate(self.ext):
                if ext[0] != '.':
                    self.ext[i] = '.' + ext

        # Overrides
        if type(self.split_char) is str:
            self.split_char = self.split_char.replace('"', '').replace("'", '')
        if type(self.split_char) is not list:
            self.split_char = list(self.split_char)
        if self.split_values is None:
            self.split_values = []

        self.get_files()

        if self.read:
            self.read_files()

    def files_to_df(self):
        """
        Method to convert file list too DataFrame

        Returns:
            self (FileReader) reference to self
        .. note:: was originally from the end of the get_files method
                  butb broken out so can apply more
        """
        # Make a DataFrame of the file paths and names
        self.file_df = pd.DataFrame({'path': self.file_list})
        if len(self.file_list) > 0:
            self.file_df['folder'] = \
                self.file_df.path.apply(
                       lambda x: os.sep.join(x.split(os.sep)[0:-1]))
            self.file_df['filename'] = \
                self.file_df.path.apply(lambda x: x.split(os.sep)[-1])
            self.file_df['ext'] = \
                self.file_df.filename.apply(lambda x: os.path.splitext(x)[-1])

            return self

    def get_files(self, reset=True):
        """
        Search directories automatically or manually by gui for file paths to
        add to self.file_list

        Args:
            reset (bool): set file list to empty if True else files are re-appended
        """

        self.file_list = [] if reset else self.file_list

        # Gui option
        if self.gui:
            self.gui_search()

        # If list of files is passed to FileReader with no scan option
        elif type(self.path) is list and self.scan != False:
            self.file_list = self.path

        # If list of files is passed to FileReader with a scan option
        elif type(self.path) is list and self.scan:
            for p in self.path:
                self.walk_dir(p)

        # If single path is passed to FileReader
        elif self.scan:
            self.walk_dir(self.path)

        # No scanning - use provided path
        else:
            self.file_list = [self.path]

        self._allfiles = [e for e in self.file_list]

        # Filter based on self.contains search string
        for contain in self.contains:
            if self.exact:
                self.file_list = [f for f in self.file_list if contain in f]
            else:
                pat = re.compile(contain)
                self.file_list = [f for f in self.file_list if pat.search(f)]

        if len(self.contains_OR) > 0:
            files = []
            for c in self.contains_OR:
                files += [f for f in self.file_list if c in f]
            self.file_list = files

        # Filter out exclude
        for exc in self.exclude:
            if self.exact:
                self.file_list = [f for f in self.file_list if exc not in f]
            else:
                pat = re.compile(exc)
                self.file_list = \
                    [f for f in self.file_list if not pat.search(f)]

        # Filter based on self.ext
        try:
            if self.ext != '':
                self.file_list = [f for f in self.file_list
                                  if os.path.splitext(f)[-1] in self.ext]
        except:
            raise ValueError('File name list is malformatted: \n   %s\nIf you '
                             'passed a path and ' % self.file_list + \
                             'meant to scan the directory, please set the '
                             '"scan" parameter to True')

        self.files_to_df()

        return self

    def gui_search(self):
        """
        Search for files using a PyQt4 gui
            Add new files to self.file_list
        """

        from PyQt4 import QtGui

        done = False
        while done != QtGui.QMessageBox.Yes:
            # Open the file dialog
            self.file_list += \
                QtGui.QFileDialog.getOpenFileNames(None,
                                                   'Pick files to open',
                                                   self.path)

            # Check if all files have been selected
            done = \
                QtGui.QMessageBox.question(None,
                                           'File search',
                                           'Finished adding files?',
                                           QtGui.QMessageBox.Yes |
                                           QtGui.QMessageBox.No,
                                           QtGui.QMessageBox.Yes)

        # Uniquify
        self.file_list = list(set(self.file_list))

        return self

    def parse_filename(self, filename, df):
        """
        Parse the filename to retrieve attributes for each file

        Args:
            filename (str): name of the file
            df (pandas.DataFrame): DataFrame containing the data found in
                filename

        Returns:
            updated DataFrame
        """

        filename = filename.split(os.path.sep)[-1]  # remove the directory
        filename = os.path.splitext(filename)[0] # remove the extension
        file_splits = []

        # Split tag values out of the filename as specified by split_values
        for i, sc in enumerate(self.split_char):
            if i == 0:
                file_splits = filename.split(sc)
            else:
                file_splits = [f.split(sc) for f in file_splits]

        if len(self.split_char) > 1:
            file_splits = [item for sublist in file_splits for item in sublist]

        # Remove initial whitespace
        if self.skip_initial_space:
            file_splits = [f.lstrip(' ') for f in file_splits]

        # Remove tag_char from split_values
        tag_splits = file_splits.copy()
        for i, fs in enumerate(file_splits):
            if self.tag_char is not None and self.tag_char in fs:
                tag_splits[i] = file_splits[i].split(self.tag_char)[0]
                file_splits[i] = file_splits[i].split(self.tag_char)[1]

        # file_splits = filename.split(self.file_split)
        if len(self.split_values)==0 or \
                str(self.split_values[0]).lower() == 'usetags':
            self.split_values = tag_splits.copy()
        for i, f in enumerate(self.split_values):
            if f is not None and i < len(file_splits) and f != file_splits[i]:
                df[f] = util.str_2_dtype(file_splits[i], ignore_list=True)

        return df

    def read_files(self, **kwargs):
        """
        Read the files in self.file_list (assumes all files can be cast into
        pandas DataFrames)
        """

        self.df, self.meta = [], []
        for i, f in enumerate(self.file_list):

            # Read the raw data file
            try:
                if self.verbose:
                    print(textwrap.fill(f,
                                        initial_indent=' '*3,
                                        subsequent_indent=' '*6))
                elif self.counter:
                    # Print a file counter
                    previous = '[%s/%s]' % ((i), len(self.file_list))
                    counter = '[%s/%s]' % ((i+1), len(self.file_list))
                    bs = len(previous)
                    if i == 0:
                        bs = 0
                    if i < len(self.file_list) - 1:
                        print('\b'*bs + counter, end='')
                    if i == len(self.file_list) - 1:
                        print('\b'*bs, end='')
                    sys.stdout.flush()

                temp = self.read_func(f, **self.kwargs)

                if type(temp) is tuple:
                    temp, meta = temp
                else:
                    meta = None

            except:
                raise ValueError('File Read Error:\n\nFilename: "%s"\n\n'
                                 'Read function: "%s".  \n\nIs the data file '
                                 'valid and uncorrupted? Or do you have the '
                                 'wrong read function specified?'
                                 % (f, self.read_func))
            # Add optional info to the table
            if type(self.labels) is list and len(self.labels) > i:
                temp['Label'] = self.labels[i]
            elif self.labels == '#':
                temp['Label'] = i
            elif type(self.labels) is str:
                temp['Label'] = self.labels

            # Optionally parse the filename to add new columns to the table
            if hasattr(self, 'split_values') and type(self.split_values) is \
                    not list:
                self.split_values = [self.split_values]
            if len(self.split_values) > 0:
                temp = self.parse_filename(f, temp)
############################################################################
# reader.py
#
#   Base file reader class
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
import re
import os
oswalk = os.walk
import pandas as pd
import pdb
import sys
import textwrap
try:
    import win32clipboard
except Exception:
    pass
from . import utilities as util
osjoin = os.path.join
st = pdb.set_trace


class FileReader():
    def __init__(self, path, **kwargs):
        """
        Reads multiple raw data files into memory based on a partial path name
        or a list of files and populates them into a single pandas DataFrame
        or a list of DataFrames

        Args:
            path (str|list): partial path name or list of files

        Keyword Args:
            contains (str|list): search string(s) used to filter the file
                list; default=''
            concat (bool):  True=concatenate all DataFrames into one |
                False=return a list of DataFrames; default=True
            exact (bool): uses exact matching in filenames if True else regex
            gui (bool):  True=use a PyQt4 gui prompt to select files |
                False=search directories automatically; default=False
            labels (list|str): adds a special label column to the DataFrame
                for distinguishing between files
                list=one entry per DataFrame added in order of self.file_list
                str=single label added to all files (ex. today's date,
                username, etc.)
            meta2df (bool): if True convert meta to concatenated DataFrame
            read (bool): read the DataFrames after compiling the file_list
            scan (bool): search subdirectories
            split_char (str|list): chars by which to split the filename
            split_values (list): values to extract from the filename based on
                file_split (ex. Filename='MyData_20151225_Wfr16.txt' -->
                file_split = '_' and split_values = [None, 'Date', 'Wafer']
            skip_initial_space (bool):  remove leading whitespace from
                split_values
            tag_char (str): split character for file tag values
                (ex. Filename='MyData_T=25C.txt' --> removes T= and adds 25C
                to a column named T
            verbose (bool): print file read progress

        """

        self.path = path
        self.contains = kwargs.get('contains', '')
        self.contains_OR = kwargs.get('contains_OR', [])
        self.exact = kwargs.get('exact', True)
        self.header = kwargs.get('header', True)
        self.concat = kwargs.get('concat', True)
        self.exclude = kwargs.get('exclude', [])
        self.ext = kwargs.get('ext', '')
        self.gui = kwargs.get('gui', False)
        self.labels = kwargs.get('labels', [])
        self.meta2df = kwargs.get('meta2df', True)
        self.scan = kwargs.get('scan', False)
        self.read = kwargs.get('read', True)
        self.include_filename = kwargs.get('include_filename', True)
        self.split_char = kwargs.get('split_char', ['_'])
        self.split_values = kwargs.get('split_values', [])
        self.skip_initial_space = kwargs.get('skip_initial_space', True)
        self.tag_char = kwargs.get('tag_char', '=')
        self.file_df = None
        self.file_list = []
        self.verbose = kwargs.get('verbose', True)
        self.read_func = kwargs.get('read_func', util.read_csv)
        self.counter = kwargs.get('counter', True)
        self.kwargs = kwargs

        # Format the contains value
        if type(self.contains) is not list:
            self.contains = [self.contains]

        # Format the contains_OR value
        if type(self.contains_OR) is not list:
            self.contains_OR = [self.contains_OR]

        # Format the exclude values
        if type(self.exclude) is not list:
            self.exclude = [self.exclude]

       # Format ext
        if self.ext != '':
            if type(self.ext) is not list:
                self.ext = [self.ext]
            for i, ext in enumerate(self.ext):
                if ext[0] != '.':
                    self.ext[i] = '.' + ext

        # Overrides
        if type(self.split_char) is str:
            self.split_char = self.split_char.replace('"', '').replace("'", '')
        if type(self.split_char) is not list:
            self.split_char = list(self.split_char)
        if self.split_values is None:
            self.split_values = []

        self.get_files()

        if self.read:
            self.read_files()

    def files_to_df(self):
        """
        Method to convert file list too DataFrame

        Returns:
            self (FileReader) reference to self
        .. note:: was originally from the end of the get_files method
                  butb broken out so can apply more
        """
        # Make a DataFrame of the file paths and names
        self.file_df = pd.DataFrame({'path': self.file_list})
        if len(self.file_list) > 0:
            self.file_df['folder'] = \
                self.file_df.path.apply(
                       lambda x: os.sep.join(x.split(os.sep)[0:-1]))
            self.file_df['filename'] = \
                self.file_df.path.apply(lambda x: x.split(os.sep)[-1])
            self.file_df['ext'] = \
                self.file_df.filename.apply(lambda x: os.path.splitext(x)[-1])

            return self

    def get_files(self, reset=True):
        """
        Search directories automatically or manually by gui for file paths to
        add to self.file_list

        Args:
            reset (bool): set file list to empty if True else files are re-appended
        """

        self.file_list = [] if reset else self.file_list

        # Gui option
        if self.gui:
            self.gui_search()

        # If list of files is passed to FileReader with no scan option
        elif type(self.path) is list and self.scan != False:
            self.file_list = self.path

        # If list of files is passed to FileReader with a scan option
        elif type(self.path) is list and self.scan:
            for p in self.path:
                self.walk_dir(p)

        # If single path is passed to FileReader
        elif self.scan:
            self.walk_dir(self.path)

        # No scanning - use provided path
        else:
            self.file_list = [self.path]

        self._allfiles = [e for e in self.file_list]

        # Filter based on self.contains search string
        for contain in self.contains:
            if self.exact:
                self.file_list = [f for f in self.file_list if contain in f]
            else:
                pat = re.compile(contain)
                self.file_list = [f for f in self.file_list if pat.search(f)]

        if len(self.contains_OR) > 0:
            files = []
            for c in self.contains_OR:
                files += [f for f in self.file_list if c in f]
            self.file_list = files

        # Filter out exclude
        for exc in self.exclude:
            if self.exact:
                self.file_list = [f for f in self.file_list if exc not in f]
            else:
                pat = re.compile(exc)
                self.file_list = \
                    [f for f in self.file_list if not pat.search(f)]

        # Filter based on self.ext
        try:
            if self.ext != '':
                self.file_list = [f for f in self.file_list
                                  if os.path.splitext(f)[-1] in self.ext]
        except:
            raise ValueError('File name list is malformatted: \n   %s\nIf you '
                             'passed a path and ' % self.file_list + \
                             'meant to scan the directory, please set the '
                             '"scan" parameter to True')

        self.files_to_df()

        return self

    def gui_search(self):
        """
        Search for files using a PyQt4 gui
            Add new files to self.file_list
        """

        from PyQt4 import QtGui

        done = False
        while done != QtGui.QMessageBox.Yes:
            # Open the file dialog
            self.file_list += \
                QtGui.QFileDialog.getOpenFileNames(None,
                                                   'Pick files to open',
                                                   self.path)

            # Check if all files have been selected
            done = \
                QtGui.QMessageBox.question(None,
                                           'File search',
                                           'Finished adding files?',
                                           QtGui.QMessageBox.Yes |
                                           QtGui.QMessageBox.No,
                                           QtGui.QMessageBox.Yes)

        # Uniquify
        self.file_list = list(set(self.file_list))

        return self

    def parse_filename(self, filename, df):
        """
        Parse the filename to retrieve attributes for each file

        Args:
            filename (str): name of the file
            df (pandas.DataFrame): DataFrame containing the data found in
                filename

        Returns:
            updated DataFrame
        """

        filename = filename.split(os.path.sep)[-1]  # remove the directory
        filename = os.path.splitext(filename)[0] # remove the extension
        file_splits = []

        # Split tag values out of the filename as specified by split_values
        for i, sc in enumerate(self.split_char):
            if i == 0:
                file_splits = filename.split(sc)
            else:
                file_splits = [f.split(sc) for f in file_splits]

        if len(self.split_char) > 1:
            file_splits = [item for sublist in file_splits for item in sublist]

        # Remove initial whitespace
        if self.skip_initial_space:
            file_splits = [f.lstrip(' ') for f in file_splits]

        # Remove tag_char from split_values
        tag_splits = file_splits.copy()
        for i, fs in enumerate(file_splits):
            if self.tag_char is not None and self.tag_char in fs:
                tag_splits[i] = file_splits[i].split(self.tag_char)[0]
                file_splits[i] = file_splits[i].split(self.tag_char)[1]

        # file_splits = filename.split(self.file_split)
        if len(self.split_values)==0 or \
                str(self.split_values[0]).lower() == 'usetags':
            self.split_values = tag_splits.copy()
        for i, f in enumerate(self.split_values):
            if f is not None and i < len(file_splits) and f != file_splits[i]:
                df[f] = util.str_2_dtype(file_splits[i], ignore_list=True)

        return df

    def read_files(self, **kwargs):
        """
        Read the files in self.file_list (assumes all files can be cast into
        pandas DataFrames)
        """

        self.df, self.meta = [], []
        for i, f in enumerate(self.file_list):

            # Read the raw data file
            try:
                if self.verbose:
                    print(textwrap.fill(f,
                                        initial_indent=' '*3,
                                        subsequent_indent=' '*6))
                elif self.counter:
                    # Print a file counter
                    previous = '[%s/%s]' % ((i), len(self.file_list))
                    counter = '[%s/%s]' % ((i+1), len(self.file_list))
                    bs = len(previous)
                    if i == 0:
                        bs = 0
                    if i < len(self.file_list) - 1:
                        print('\b'*bs + counter, end='')
                    if i == len(self.file_list) - 1:
                        print('\b'*bs, end='')
                    sys.stdout.flush()

                temp = self.read_func(f, **self.kwargs)

                if type(temp) is tuple:
                    temp, meta = temp
                else:
                    meta = None

            except:
                raise ValueError('File Read Error:\n\nFilename: "%s"\n\n'
                                 'Read function: "%s".  \n\nIs the data file '
                                 'valid and uncorrupted? Or do you have the '
                                 'wrong read function specified?'
                                 % (f, self.read_func))
            # Add optional info to the table
            if type(self.labels) is list and len(self.labels) > i:
                temp['Label'] = self.labels[i]
            elif self.labels == '#':
                temp['Label'] = i
            elif type(self.labels) is str:
                temp['Label'] = self.labels

            # Optionally parse the filename to add new columns to the table
            if hasattr(self, 'split_values') and type(self.split_values) is \
                    not list:
                self.split_values = [self.split_values]
            if len(self.split_values) > 0:
                temp = self.parse_filename(f, temp)

            # Add filename
            if self.include_filename:
                temp['Filename'] = f
                if type(meta) is pd.DataFrame or type(meta) is dict:
                    meta['Filename'] = f
                elif type(meta) is pd.Series:
                    meta.ix['Filename', :] = f
            self.df += [temp]
            if meta is not None:
                self.meta += [meta]

        if self.concat and len(self.df) > 0:
            self.temp = temp
            self.df = pd.concat(self.df, axis=0)
            if len(self.meta) > 0:
                self.meta = \
                    pd.concat(self.meta, axis=1).reset_index(drop=True) \
                        if self.meta2df else self.meta
            elif self.meta2df:
                self.meta = pd.DataFrame()

    def walk_dir(self, path):
        """
        Walk through a directory and its subfolders to find file names

        Args:
            path (str): top level directory

        """

        for dir_name, subdir_list, file_list in oswalk(path):
            for exc in self.exclude:
                subdir_list[:] = [s for s in subdir_list if exc not in s]
            self.file_list += [os.path.join(dir_name, f) for f in file_list]

            # Add filename
            if self.include_filename:
                temp['Filename'] = f
                if meta is not None:
                    meta.ix['Filename', :] = f
            self.df += [temp]
            if meta is not None:
                self.meta += [meta]

        if self.concat and len(self.df) > 0:
            self.temp = temp
            self.df = pd.concat(self.df, axis=0)
            if len(self.meta) > 0:
                self.meta = \
                    pd.concat(self.meta, axis=1).T.reset_index(drop=True) \
                        if self.meta2df else self.meta
            elif self.meta2df:
                self.meta = pd.DataFrame()

    def walk_dir(self, path):
        """
        Walk through a directory and its subfolders to find file names

        Args:
            path (str): top level directory

        """

        for dir_name, subdir_list, file_list in oswalk(path):
            for exc in self.exclude:
                subdir_list[:] = [s for s in subdir_list if exc not in s]
            self.file_list += [os.path.join(dir_name, f) for f in file_list]
