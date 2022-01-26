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
import json

########################################################
########################################################

# FUNCTIONS

def removeAppDir(dir_name):

    tmp_dir = getSystemTempDir()
    out_dir = os.path.join(tmp_dir, dir_name)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)

    return out_dir

def createCustomTempDir(dir_name):

    out_dir = removeAppDir(dir_name)
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

def readJSONConfigFile(dir_name):

    if os.path.exists(os.path.join(dir_name, "config_file.json")):
        with open(os.path.join(dir_name, "config_file.json")) as f:
            json_config_file = json.load(f)

    return json_config_file

########################################################
########################################################
