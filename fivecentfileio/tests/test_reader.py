import os, sys, pdb
st = pdb.set_trace
osjoin, osplit, abspath = os.path.join, os.path.split, os.path.abspath
DIR = osplit(os.path.realpath(__file__))[0]
path = abspath('..\..')
sys.path.insert(0, path) if path not in sys.path else None
import fileio


def test_meta_length():

    # Case file not found
    file = 'unheavenly_creatures.csv'
    lines = fileio.utilities.meta_length(file)
    assert lines == -1

    # Case found
    file = osjoin(DIR, 'data_key_example.csv')
    lines = fileio.utilities.meta_length(file)
    assert lines == 4

    # Case found and next line
    lines = fileio.utilities.meta_length(file, next_line=True)
    assert lines == (4, 'Coheed,Jane,Sue')

    # Case not found bad keyword read all
    lines = fileio.utilities.meta_length(file, 'boom')
    assert lines == -1

    # Case not found limited lines
    lines = fileio.utilities.meta_length(file, max_lines=1)
    assert lines == -1

    # .gzip compressed file tests

    # Case found
    file = osjoin(DIR, 'data_key_example.csv.gz')
    lines = fileio.utilities.meta_length(file)
    assert lines == 4

    # Case found and next line
    lines = fileio.utilities.meta_length(file, next_line=True)
    assert lines == (4, 'Coheed,Jane,Sue')

    # Case not found bad keyword read all
    lines = fileio.utilities.meta_length(file, 'boom')
    assert lines == -1

    # Case not found limited lines
    lines = fileio.utilities.meta_length(file, max_lines=1)
    assert lines == -1


def test_read_csv():

    # Case of simple csv
    file = osjoin(DIR, 'simple_csv_example.csv')
    df = fileio.utilities.read_csv(file)
    assert df.loc[0, 'Coheed'] == 1

    # Case of simple file with different delimiter
    file = osjoin(DIR, 'simple_non-csv_example.csv')
    df = fileio.utilities.read_csv(file, sep=';')
    assert df.loc[0, 'Coheed'] == 1

    # Case of simple gzip csv
    file = osjoin(DIR, 'simple_csv_example.csv.gz')
    df = fileio.utilities.read_csv(file)
    assert df.loc[0, 'Coheed'] == 1

    # Case of simple gzip file with different delimiter
    file = osjoin(DIR, 'simple_non-csv_example.csv.gz')
    df = fileio.utilities.read_csv(file, sep=';')
    assert df.loc[0, 'Coheed'] == 1


def test_read_data():

    # Case of meta
    file = osjoin(DIR, 'data_key_example.csv')
    df, meta = fileio.utilities.read_data(file, data_key='[DATA]')
    assert df.loc[0, 'Coheed'] == 1
    assert meta.loc[0, 'Meta1'] == 1

    # Case of meta with gz
    file = osjoin(DIR, 'data_key_example.csv.gz')
    df, meta = fileio.utilities.read_data(file, data_key='[DATA]')
    assert df.loc[0, 'Coheed'] == 1
    assert meta.loc[0, 'Meta1'] == 1


def test_write_data():

    file = osjoin(DIR, 'data_key_example.csv')
    df, meta = fileio.utilities.read_data(file, data_key='[DATA]')
    fileio.utilities.write_data('test.csv', df, meta, data_key='[DATA]')
    df, meta = fileio.utilities.read_data('test.csv', data_key='[DATA]')
    assert df.loc[0, 'Coheed'] == 1
    assert meta.loc[0, 'Meta1'] == 1
    os.remove('test.csv')

    file = osjoin(DIR, 'data_key_example.csv')
    df, meta = fileio.utilities.read_data(file, data_key='[DATA]')
    fileio.utilities.write_data('test.csv.gz', df, meta, data_key='[DATA]')
    df, meta = fileio.utilities.read_data('test.csv.gz', data_key='[DATA]')
    assert df.loc[0, 'Coheed'] == 1
    assert meta.loc[0, 'Meta1'] == 1
    os.remove('test.csv.gz')


def test_align_values():

    file = osjoin(DIR, 'data_key_example.csv')
    df, meta = fileio.utilities.read_data(file, data_key='[DATA]')
    df = fileio.utilities.align_values(df, first_col=0, rjust=True)
    assert df.loc[0, 'Coheed'] == '     1'

