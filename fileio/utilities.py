############################################################################
# utilities.py
#   Utility functions for reading and parsing
############################################################################
__author__    = 'Steve Nicholes'
__copyright__ = 'Copyright (C) 2017 Steve Nicholes'
__license__   = 'GPLv3'
__version__   = '0.1.0'
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
try:
    import win32clipboard
except Exception:
    pass
from docutils import core
osjoin = os.path.join
st = pdb.set_trace


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
        img = img.replace('.. figure:: ', '').replace('\n', '')
        if ' ' in img:
            img_ns = img.replace(' ','')
            idx = html.find(img_ns) - 5
            old = 'alt="%s" src="%s"' % (img_ns, img_ns)
            new = 'alt="%s" src="%s"' % (img, img)
            html = html[0:idx] + new + html[idx+len(old):]

            with open(file_dest, 'w') as output:
                output.write(html)

    # Case of substituted images
    imgs = [f for f in rst if 'image::' in f]

    for img in imgs:
        img = img.replace('.. image:: ', '').replace('\n', '')
        if ' ' in img:
            img_ns = img.replace(' ','')
            idx = html.find(img_ns) - 5
            old = 'alt="%s" src="%s"' % (img_ns, img_ns)
            new = 'alt="%s" src="%s"' % (img, img)
            html = html[0:idx] + new + html[idx+len(old):]

            with open(file_dest, 'w') as output:
                output.write(html)

    # Case of links
    links = [f for f in rst if ">`_" in f]

    for link in links:
        link = re.search("<(.*)>`_", link).group(1)
        if ' ' in link:
            link_ns = link.replace(' ','')
            idx = html.find(link_ns)
            html = html[0:idx] + link + html[idx+len(link_ns):]


            with open(file_dest, 'w') as output:
                output.write(html)


def read_csv(file_name, **kwargs):
    """
    Wrapper for pandas.read_csv to deal with kwargs overload

    Args:
        file_name (str): filename
        **kwargs: valid keyword arguments for pd.read_csv

    Returns:
        pandas.DataFrame containing the csv data
    """

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

    delkw = [f for f in kwargs.keys() if f not in kw_master]
    for kw in delkw:
        kwargs.pop(kw)

    return pd.read_csv(file_name, **kwargs)


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
    v = val.split('#')
    if len(v) > 1:  # handle comments
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
            k += [str_2_dtype(t.split(':')[0], ignore_list=True)]
            v += [str_2_dtype(':'.join(t.split(':')[1:]))]
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
                return val.rstrip().lstrip()


