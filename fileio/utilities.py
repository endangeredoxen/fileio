############################################################################
# utilities.py
#   Utility functions for reading and parsing
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
import pandas as pd
import pdb
import re
import ast
import stat
import sys
import gzip
try:
    import win32clipboard
except Exception:
    pass
from docutils import core
osjoin = os.path.join
osexists = os.path.exists
st = pdb.set_trace
print_std = print


def _is_gz(filename):
    """
    Check if gzip compressed by file extension
     (not supporting arbitrary compression types here)
    """
    return True if filename[-3:] == '.gz' else False


def align_values(df, rjust=True, first_col=2):
    """
    Pad the value and column names of a dataframe with space to line them up
        for a more readable format

    Args:
        df (pd.DataFrame): data to align
        rjust (bool):  right justification enabled (if false, left justified)
        first_col (int): extra whitespace for first columns [default = 2]

    Return:
        update DataFrame

    """

    df = df.copy()
    names = []
    columns = df.columns
    for icol, col in enumerate(columns):
        # Find the longest element in the column
        value_len = max([len(str(f)) for f in df[col].unique()])
        name_len = len(col)
        width = max(value_len, name_len) + (first_col if icol == 0 else 0)

        # Adjust the column names
        if rjust:
            names += [' ' * (width - len(col)) + col]
        else:
            names += [col + ' ' * (width - len(col))]

        # Adjust the column values
        df[col] = df[col].astype(str)
        if rjust:
            df[col] = df[col].apply(lambda x: ' ' * (width - len(x)) + x)
        else:
            df[col] = df[col].apply(lambda x: x + ' ' * (width - len(x)))

    df.columns = names

    return df


def check_file(filename, verbose=True):
    """
    Check if file exists

    Args:
        filename (str): path to file

    Returns:
        boolean True if found

    """

    # Check if file exists
    if os.path.exists(filename):
        return True
    else:
        if verbose:
            print('MissingFileError: %s could not be found' % filename)
        return False


def convert_rst(file_name, stylesheet=None):
    """ Converts single rst files to html

    Adapted from Andrew Pinion's solution @
    http://halfcooked.com/blog/2010/06/01/generating-html-versions-of-
        restructuredtext-files/

    Args:
        file_name (str): name of rst file to convert to html
        stylesheet (str): optional path to a stylesheet

    Returns:
        None
    """

    settings_overrides=None
    if stylesheet is not None:
        if type(stylesheet) is not list:
            stylesheet = [stylesheet]
        settings_overrides = {'stylesheet_path':stylesheet}
    source = open(file_name, 'r')
    file_dest = os.path.splitext(file_name)[0] + '.html'
    destination = open(file_dest, 'w')
    core.publish_file(source=source, destination=destination,
                      writer_name='html',
                      settings_overrides=settings_overrides)
    source.close()
    destination.close()

    # Fix issue with spaces in figure path and links
    with open(file_name, 'r') as input:
        rst = input.readlines()

    with open(file_dest, 'r') as input:
        html = input.read()

    # Case of figures
    imgs = [f for f in rst if 'figure::' in f]
    for img in imgs:
        img = img.replace('.. figure:: ', '').replace('\n', '').lstrip()
        if ' ' in img:
            img_ns = img.replace(' ','').replace('\\', '')
            idx = html.find(img_ns) - 5
            if idx < 0:
                continue
            old = 'alt="%s" src="%s"' % (img_ns, img_ns)
            new = 'alt="%s" src="%s"' % (img, img)
            html = html[0:idx] + new + html[idx+len(old):]

            with open(file_dest, 'w') as output:
                output.write(html)

    # Case of substituted images
    imgs = [f for f in rst if 'image::' in f]
    for img in imgs:
        img = img.replace('.. image:: ', '').replace('\n', '').lstrip()
        if ' ' in img:
            img_ns = img.replace(' ','').replace('\\', '')
            idx = html.find(img_ns) - 5
            if idx < 0:
                continue
            old = 'alt="%s" src="%s"' % (img_ns, img_ns)
            new = 'alt="%s" src="%s"' % (img, img)
            html = html[0:idx] + new + html[idx+len(old):]

            with open(file_dest, 'w') as output:
                output.write(html)

    # Case of links
    links = [f for f in rst if ">`_" in f]
    for link in links:
        try:
            link = re.search("<(.*)>`_", link).group(1)
        except:
            print('invalid rst link: "%s"' % link)
            continue
        if ' ' in link:
            link_ns = link.replace(' ','')
            idx = html.find(link_ns)
            html = html[0:idx] + link + html[idx+len(link_ns):]


            with open(file_dest, 'w') as output:
                output.write(html)


def get_mtime(file):
    """
    Get the modified time of a file
        Handles exceptions

    Args:
        file (str): filename

    Returns:
        modified timestamp

    """

    try:
        return os.path.getmtime(file)
    except:
        return 0


def print(text, verbose=True, post_text='', line_len=79,
          start='\r', end='\n', **kwargs):
    """
    Custom print wrapper with fixed line length and optional
    completion text.  If start is not a new line char, message
    writes over existing line

    Args:
        text (str):  main text to display
        verbose (bool):  toggle print text on/off
        post_text (str):  text to append at end of line
        line_len (int):  length of message; shorter text strings filled
            with '.'
        start (str):  initial text (such as new line char)
        end (str):  ending text (such as new line char)
        **kwargs:  python print function keyword args

    """

    text = start + text
    text += '.' * (line_len - len(text)) + post_text

    if verbose:
        print_std(text, end=end)
        sys.stdout.flush()


def meta_length(filename, data_keys=['[DATA]'], max_lines=None, next_line=False,
                verbose=True):
    """
    For text files containing meta and raw data separated by one or more keys,
    returns the number of rows of meta data

    File is read line by line until one of the data_keys is found

    Ex file setup:
        Meta name 1,value1
        Meta name 2,value2
        .
        .
        .
        [data]
        Data name 1,Data name 2,...,Data name X
        1,2,...,8
        2,3,...,10

    Args:
        filename (str):  string path to the file of interest
        data_keys (list | str):  keywords in the file used to designate the meta
            region from the rest of the file
        max_lines (None | int):  set a limit on how many lines of the file
            are checked
        next_line (bool):  optionally return the next line in the file if data key
            is found
        verbose (bool):  toggle printing of warnings

    Returns:
        int number of rows for the meta section of a file, optional line after
        the data separator with next_line = True

    """

    # Ensure data_keys is a list
    data_keys = validate_list(data_keys)

    # Check if file exists
    exists = check_file(filename, verbose)
    if not exists:
        return -1

    def _parse_meta(file):
        for iline, line in enumerate(file):
            found = any(key in line for key in data_keys)
            if found and next_line:
                return iline + 1, next(file).strip('\r').strip('\n')
            elif found:
                return iline + 1
            if max_lines is not None and iline + 1 >= max_lines:
                return -1
        return -1

    # Parse the meta section of the file
    if _is_gz(filename):
        with gzip.open(filename, "rt") as file:
            return _parse_meta(file)

    with open(filename, 'r') as file:
        return _parse_meta(file)


def read_csv(filename, data_key=None, sep_meta=None, **kwargs):
    """
    Wrapper for pandas.read_csv to deal with kwargs overload

    Args:
        filename (str): filename
        data_key (None | list | str):  keys to separate the data file into
            a meta and data section; uses meta_length to find the split between
            sections
        sep_meta (None | str):  optional different character for parsing
            the meta section
        **kwargs: valid keyword arguments for pd.read_csv

    Returns:
        pandas.DataFrame containing the csv data and optional meta dataframe
    """

    verbose = kwargs.get('verbose', True)

    # Check if file exists
    exists = check_file(filename, verbose)
    if not exists:
        return -1

    # kwargs may contain values that are not valid in the read_csv function;
    #  we need to filter those out first before calling the function
    kw_master = ['filepath_or_buffer', 'sep', 'dialect', 'compression',
                 'doublequote', 'escapechar', 'quotechar', 'quoting',
                 'skipinitialspace', 'lineterminator', 'header', 'index_col',
                 'names', 'prefix', 'skiprows', 'skipfooter', 'skip_footer',
                 'na_values', 'true_values', 'false_values', 'delimiter',
                 'converters', 'dtype', 'usecols', 'engine',
                 'delim_whitespace', 'as_recarray', 'na_filter',
                 'compact_ints', 'use_unsigned', 'low_memory', 'buffer_lines',
                 'warn_bad_lines', 'error_bad_lines', 'keep_default_na',
                 'thousands', 'comment', 'decimal', 'parse_dates',
                 'keep_date_col', 'dayfirst', 'date_parser', 'memory_map',
                 'float_precision', 'nrows', 'iterator', 'chunksize',
                 'verbose', 'encoding', 'squeeze', 'mangle_dupe_cols',
                 'tupleize_cols', 'infer_datetime_format', 'skip_blank_lines']

    # Deal with keywords
    delkw = [f for f in kwargs.keys() if f not in kw_master]
    for kw in delkw:
        kwargs.pop(kw)
    if 'skipinitialspace' not in kwargs.keys():
        kwargs['skipinitialspace'] = True

    # Read the data section
    df = pd.read_csv(filename, **kwargs)

    return df


def read_data(filename, data_key=None, sep_meta=None, **kwargs):
    """
    Wrapper for pandas.read_csv to deal with kwargs overload

    Args:
        filename (str): filename
        data_key (None | list | str):  keys to separate the data file into
            a meta and data section; uses meta_length to find the split between
            sections
        sep_meta (None | str):  optional different character for parsing
            the meta section
        **kwargs: valid keyword arguments for pd.read_csv

    Returns:
        pandas.DataFrame containing the csv data and optional meta dataframe
    """

    verbose = kwargs.get('verbose', True)

    # Check if file exists
    exists = check_file(filename, verbose)
    if not exists:
        return -1, -1

    # Check for a meta section
    if data_key is not None:
        skiprows = meta_length(filename, data_key, verbose=verbose)
    else:
        skiprows = None

    # Read the data section
    df = read_csv(filename, skiprows=skiprows, **kwargs)

    # Read the meta section
    if data_key is not None and skiprows > 0:
        if sep_meta is None:
            if 'sep_meta' in kwargs.keys():
                sep_meta = kwargs['sep_meta']
            elif 'sep' in kwargs.keys():
                sep_meta = kwargs['sep']
            else:
                sep_meta = ','
        meta = read_meta(filename, data_key, sep_meta, verbose=verbose)
        return df, meta

    else:
        return df


def read_meta(filename, data_keys, sep=',', max_lines=None, verbose=True):
    """
    Read the meta section of a data file containing meta and raw data

    Args:
        filename (str): path to data
        data_keys (list | str):  keywords in the file used to designate the meta
            region from the rest of the file
        sep (str): delimiter for meta data
        max_lines (None | int):  set a limit on how many lines of the file
            are checked
        verbose (bool):  toggle printing of warnings

    Returns:
        pd.DataFrame of meta data or -1 if file does not exist

    """

    # Check if file exists
    exists = check_file(filename, verbose)
    if not exists:
        return -1

    # Get number of lines
    if max_lines is None:
        skiprows = meta_length(filename, data_keys)

    def _parse_meta(file):
        key = []
        val = []
        for iline, line in enumerate(file):
            if iline < skiprows - 1:
                vals = line.split(sep)
                key += [vals[0]]
                val += [str_2_dtype(vals[1].lstrip(' ')
                        .strip('\n').strip('\r'))]
        meta = pd.DataFrame(val).T
        meta.columns = key

        return meta

    if _is_gz(filename):
        with gzip.open(filename, "rt") as file:
            return _parse_meta(file)
    else:
        with open(filename, 'r') as file:
            return _parse_meta(file)


def set_filemode(name, stmode='r'):
    """
    Set file mode to read or write

    Args:
        name (str): full path to file

    Keyword Args:
        stmode (str or stat.ST_MODE, ``r``):  ``r``, ``w``, or stat.ST_MODE

    Returns:
        name (str): name parameter passed through
    """
    if not os.path.isfile(name):
        raise ValueError('not a valid file: ' + name)

    if stmode == 'r':
        stmode = stat.S_IREAD

    if stmode == 'w':
        stmode = stat.S_IWRITE

    mode_ = os.stat(name)[stat.ST_MODE]

    if stmode == mode_:
        return

    os.chmod(name, stmode)

    return name


def str_2_dtype(val, ignore_list=False):
    """
    Convert a string to the most appropriate data type
    Args:
        val (str): string value to convert
        ignore_list (bool):  ignore option to convert to list

    Returns:
        val with the interpreted data type
    """

    # Special chars
    chars = {'\\t':'\t', '\\n':'\n', '\\r':'\r'}

    # Remove comments
    v = re.split("#(?=([^\"]*\"[^\"]*\")*[^\"]*$)", val)
    if len(v) > 1:  # handle comments
        v = [f for f in v if f is not None]
        if v[0] == '':
            val = '#' + v[1].rstrip().lstrip()
        else:
            val = v[0].rstrip().lstrip()

    # Special
    if val in chars.keys():
        val = chars[val]
    # None
    if val == 'None':
        return None
    # bool
    if val == 'True':
        return True
    if val == 'False':
        return False
    # dict
    if ':' in val and '{' in val:
        val = val.replace('{','').replace('}','')
        val = re.split(''',(?=(?:[^'"]|'[^']*'|"[^"]*")*$)''', val)
        k = []
        v = []
        for t in val:
            tt = re.split(''':(?=(?:[^'"]|'[^']*'|"[^"]*")*$)''', t)
            k += [str_2_dtype(tt[0], ignore_list=True)]
            v += [str_2_dtype(':'.join(tt[1:]))]
        return dict(zip(k,v))
    # tuple
    if val[0] == '(' and val[-1] == ')' and ',' in val:
        return ast.literal_eval(val)
    # list
    if (',' in val or val.lstrip(' ')[0] == '[') and not ignore_list \
            and val != ',':
        if val[0] == '"' and val[-1] == '"' and ', ' not in val:
            return str(val.replace('"', ''))
        if val.lstrip(' ')[0] == '[':
            val = val.lstrip('[').rstrip(']')
        val = val.replace(', ', ',')
        new = []
        val = re.split(',(?=(?:"[^"]*?(?: [^"]*)*))|,(?=[^",]+(?:,|$))', val)
        for v in val:
            if '=="' in v:
                new += [v.rstrip().lstrip()]
            elif '"' in v:
                double_quoted = [f for f in re.findall(r'"([^"]*)"', v)
                                 if f != '']
                v = str(v.replace('"', ''))
                for dq in double_quoted:
                    v = v.replace(dq, '"%s"' % dq)
                try:
                    if type(ast.literal_eval(v.lstrip())) is str:
                        v = ast.literal_eval(v.lstrip())
                    new += [v]
                except:
                    new += [v.replace('"','').rstrip().lstrip()]
            else:
                try:
                    new += [str_2_dtype(v.replace('"','').rstrip().lstrip())]
                except RecursionError:
                    pass
        if len(new) == 1:
            return new[0]
        return new
    # float and int

    try:
        int(val)
        return int(val)
    except:
        try:
            float(val)
            return float(val)
        except:
            v = val.split('#')
            if len(v) > 1:  # handle comments
                if v[0] == '':
                    return '#' + v[1].rstrip().lstrip()
                else:
                    return v[0].rstrip().lstrip()
            else:
                val = val.rstrip().lstrip()
                if val[0] in ['"', "'"] and val[-1] in ['"', "'"]:
                    return val.strip('\'"')
                else:
                    return val


def write_data(filename, df, meta=None, data_key='[DATA]', align=False, **kwargs):
    """
    Write data files containing a meta section, separator keyword, and raw data

    Args:
        filename (str): output file path
        df (pd.DataFrame):  DataFrame to save
        meta (None | pd.DataFrame): optional meta data to proceed the
            data section
        data_key (str): separator between meta and df
        align (bool): pad values to align csv and make it more human readable

    Returns:
        None

    """

    sep_meta = kwargs.get('sep_meta', ',')
    sep = kwargs.get('sep', ',')
    first_col = kwargs.get('first_col', 0)
    rjust = kwargs.get('rjust', True)

    # Write meta data
    if meta is not None:
        meta.T.to_csv(filename, mode='w', header=False, sep=sep_meta)

    # Write data separator
    if meta is not None:
        mode = 'a'
        with open(filename, mode) as output:
            output.write('%s\n' % data_key)
    else:
        mode = 'w'

    # Align the raw data
    df = align_values(df, first_col=first_col, rjust=rjust) if align else df

    # Write the raw data
    df.to_csv(filename, index=False, mode=mode, sep=sep)


def validate_list(items):
    """
    Make sure a list variable is actually a list and not a single string

    Args:
        items (str|list): values to check dtype

    Return:
        items as a list
    """

    if items is None:
        return None
    if type(items) is tuple:
        return list(items)
    elif type(items) is not list:
        return [items]
    else:
        return items