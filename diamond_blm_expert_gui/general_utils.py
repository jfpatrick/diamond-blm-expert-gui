########################################################
########################################################

# GUI created by: martinja
# Contact: javier.martinez.samblas@cern.ch

########################################################
########################################################

# IMPORTS

import os
import tempfile
import shutil

########################################################
########################################################

# FUNCTIONS

def createCustomTempDir(dir_name):

    tmp_dir = getSystemTempDir()
    out_dir = os.path.join(tmp_dir, dir_name)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.mkdir(out_dir)

    return out_dir

def getSystemTempDir():

    try:
        tmp_dir = tempfile.gettempdir()
    except:
        try:
            tmp_dir = os.path.expanduser('~')
        except:
            tmp_dir = ""

    return tmp_dir

########################################################
########################################################
