############################################################################
# html.py
#
#   Classes and functions for reading and outputting html-based files
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
import pandas as pd
import pdb
import pathlib
try:
    import win32clipboard
except Exception:
    pass
from xml.dom import minidom
from xml.etree import ElementTree
import numpy as np
from natsort import natsorted
from . import utilities as util
osjoin = os.path.join
st = pdb.set_trace


class Dir2HTML():
    def __init__(self, base_path, ext=None, **kwargs):
        """
        Directory to unordered html list (UL) conversion tool

        Args:
            base_path (str): top level directory or path to a list of files to
                             use in the UL
            ext (list): file extensions to include when building file list

        Keyword Args:
            build_rst (bool): convert rst files to html
            exclude (list): names of files to exclude from the UL
            from_file (bool): make the report from a text file containing a
                list of directories and files or just scan the
                base_path directory
            natsort (bool): use natural (human) sorting on the file list
            onclick (bool): enable click to open for files listed in the UL
            onmouseover (bool): enable onmouseover viewing for files listed in
                the UL
            rst_css (str): path to css file for rst files
            show_ext (bool): show/hide file extension in the file list

        Returns:

        """

        self.base_path = base_path
        self.build_rst = kwargs.get('build_rst', False)
        self.exclude = kwargs.get('exclude',[])
        self.files = []
        self.from_file = kwargs.get('from_file', False)
        self.natsort = kwargs.get('natsort', True)
        self.onclick = kwargs.get('onclick', None)
        self.onmouseover = kwargs.get('onmouseover', None)
        self.rst = ''
        self.rst_css = kwargs.get('rst_css', None)
        self.show_ext = kwargs.get('show_ext', False)
        self.ul = '<ul>'
        self.use_relative = kwargs.get('use_relative', True)

        self.ext = ext
        if self.ext is not None and type(self.ext) is not list:
            self.ext = self.ext.replace(' ','').split(',')
            self.ext = [f.lower() for f in self.ext]

        self.get_files(self.from_file)

        if len(self.files) > 0:
            if self.build_rst:
                self.make_html()
            self.filter()
            self.drop_duplicates()
            self.nan_to_str()
            self.make_links()
            self.make_ul()

    def df_to_xml(self, df, parent_node=None, parent_name=''):
        """
        Builds an xml structure from a DataFrame

        Args:
            df (DataFrame):  directory structure
            parent_node (node|None):  parent node in the xml structure
            parent_name (str|''):  string name of the node

        Returns:
            node:  ElementTree xml representation of df
        """


        def node_for_value(name, value, parent_node, parent_name,
                           dir=False, set_id=None):
            """
            creates the <li><input><label>...</label></input></li> elements.
            returns the <li> element.
            """

            node= ElementTree.SubElement(parent_node, 'li')
            child= ElementTree.SubElement(node, 'A')
            if set_id is not None:
                child.set('id', set_id)
            if self.onmouseover and not dir:
                child.set('onmouseover', self.onmouseover+"('"+value+"')")
            if self.onclick and not dir:
                child.set('onclick', self.onclick+"('"+value+"')")
                child.set('href', 'javascript:void(0)')
            elif self.onclick and dir:
                child.set('onclick', self.onclick+"('"+value+"')")
                child.set('href', 'javascript:void(0)')
            child.text= name
            return node

        subdirs = [f for f in df.columns if 'subdir' in f]

        if parent_node is None:
            node = ElementTree.Element('ul')
        else:
            node = ElementTree.SubElement(parent_node, 'ul')
        node.set('id', 'collapse')

        if len(subdirs) > 0:
            groups = df.groupby(subdirs[0])
            for i, (n, g) in enumerate(groups):
                del g[subdirs[0]]
                if n == 'nan':
                    for row in range(0,len(g)):
                        node_for_value(g.filename.iloc[row],
                                       g.html_path.iloc[row], node,
                                       parent_name, set_id='image_link')
                else:
                    current_path_list = g.full_path.iloc[0].split(os.path.sep)
                    path_idx = current_path_list.index(n)
                    folder_path = \
                        os.path.sep.join(current_path_list[0:path_idx+1])
                    if self.use_relative:
                        folder_path = folder_path.replace(self.base_path + '\\', '')
                        folder_path = folder_path.replace('\\', '/')
                    else:
                        folder_path = pathlib.Path(folder_path).as_uri()
                    child = node_for_value(n, folder_path, node,
                                           parent_name, dir=True)
                    self.df_to_xml(g, child, n)

        else:
            for row in range(0,len(df)):
                node_for_value(df.filename.iloc[row], df.html_path.iloc[row],
                               node, parent_name, set_id='image_link')

        return node

    def drop_duplicates(self):
        """
        Remove duplicate values and for image + html, reduce to one link
        """

        # Drop complete duplicates
        self.files = self.files.drop_duplicates().reset_index(drop=True)

        # Condense html + image file pairs
        dups = self.files['filename'].duplicated()
        dup_idx = list(dups[dups].index)
        for ii, idx in enumerate(dup_idx):
            if self.files.loc[idx, 'ext'] != 'html':
                dup_idx[ii] = idx - 1
        self.files = self.files.drop(dup_idx).reset_index(drop=True)

    def get_files(self, from_file):
        """
        Get the files for the report

        Args:
            from_file (bool):  use a text file to identify the directories
                and files to be used in the report

        """

        if from_file:
            # Build the list from a text file
            with open(self.base_path,'r') as input:
                files = input.readlines()
            temp = pd.DataFrame()
            files = [f.strip('\n') for f in files if len(f) > 0]
            for f in files:
                self.base_path = f
                self.get_files(False)
                temp = pd.concat([temp,self.files])
            self.files = temp.reset_index(drop=True)

        else:
            # Walk the base_path to identify all the files for the report
            self.files = []
            for dirName, subdirList, fileList in oswalk(self.base_path):
                if self.ext is not None:
                    fileList = [f for f in fileList
                                if f.split('.')[-1].lower() in self.ext]
                for fname in fileList:
                    temp = {}
                    temp['full_path'] = \
                        os.path.abspath(osjoin(self.base_path,dirName,fname))
                    temp['rel_path'] = \
                        temp['full_path'].replace(self.base_path+'\\', '')
                    if self.use_relative:
                        temp['html_path'] = temp['rel_path'].replace('\\', '/')
                    else:
                        temp['html_path'] = \
                            pathlib.Path(temp['full_path']).as_uri()
                    temp['ext'] = fname.split('.')[-1]
                    if self.from_file:
                        top = self.base_path.split(os.sep)[-1]
                        subdirs = temp['full_path']\
                                  .replace(self.base_path.replace(top,''),'')\
                                  .split(os.sep)
                    else:
                        subdirs = temp['full_path']\
                                  .replace(self.base_path+os.sep,'')\
                                  .split(os.sep)
                    temp['base_path'] = self.base_path
                    for i,s in enumerate(subdirs[:-1]):
                        temp['subdir%s' % i] = s
                    temp['filename_ext'] = subdirs[-1]
                    temp['filename'] = os.path.splitext(subdirs[-1])[0]
                    self.files += [temp]

            if len(self.files) == 0 and os.path.exists(self.base_path) \
                    and self.base_path.split('.')[-1] in self.ext:
                temp = {}
                temp['full_path'] = os.path.abspath(self.base_path)
                temp['html_path'] = pathlib.Path(temp['full_path']).as_uri()
                subdirs = temp['full_path'].split(os.sep)
                temp['base_path'] = os.sep.join(subdirs[0:-1])
                temp['filename'] = subdirs[-1]
                self.files += [temp]

            self.files = pd.DataFrame(self.files)

            # Sort the files
            if self.natsort and len(self.files) > 0:
                temp = self.files.set_index('full_path')
                self.files = \
                    temp.reindex(index=natsorted(temp.index)).reset_index()

    def filter(self):
        """
        Filter out any files on the exclude list
        """

        for ex in self.exclude:
            self.files = \
                self.files[~self.files.full_path.str.contains(ex, regex=False)]

        self.files = self.files.reset_index(drop=True)

    def make_html(self):
        """
        Build html files from rst files
        """

        self.rst = self.files[self.files.ext=='rst']
        idx_to_drop = []
        for i, f in self.rst.iterrows():
            util.convert_rst(f['full_path'], stylesheet=self.rst_css)
            self.files.iloc[i]['ext'] = 'html'
            self.files.iloc[i]['filename'] = \
                self.files.iloc[i]['filename'].replace('rst','html')
            self.files.iloc[i]['filename_ext'] = \
                self.files.iloc[i]['filename_ext'].replace('rst','html')
            self.files.iloc[i]['full_path'] = \
                self.files.iloc[i]['full_path'].replace('rst','html')
            self.files.iloc[i]['html_path'] = \
                self.files.iloc[i]['html_path'].replace('rst','html')
            self.files.iloc[i]['rel_path'] = \
                self.files.iloc[i]['rel_path'].replace('rst','html')

            # Check for same-named images
            for ext in [v for v in self.ext if v != 'html']:
                idx = self.files.query('full_path==r"%s"' %
                              self.files.iloc[i]['full_path']
                                       .replace('html',ext)) \
                                       .index
                if len(idx) > 0:
                    idx_to_drop += list(idx)

        self.files = self.files.drop(idx_to_drop).reset_index(drop=True)

    def make_links(self):
        """
        Build the HTML links
        """

        self.files['link'] = '''<A onmouseover="div_switch(' ''' + \
                             self.files.html_path.map(str) + \
                             '''')" onclick="HREF=window.open(' ''' + \
                             self.files.html_path.map(str) + \
                             '''')"href="javascript:void(0)">''' + \
                             self.files.filename.map(str) + \
                             '''</A><br>'''

    def make_ul(self):
        """
        Convert the DataFrame of paths and files to xml
        """

        element= self.df_to_xml(self.files)
        xml = ElementTree.tostring(element)
        xml = minidom.parseString(xml)
        self.ul = xml.toprettyxml(indent='  ')
        self.ul = self.ul.replace('<?xml version="1.0" ?>\n', '')

    def nan_to_str(self):
        """
        Replace NaN with a string version
        """

        self.files = self.files.replace(np.nan, 'nan')

