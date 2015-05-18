# This is a demo reduce.py script

import sys
import os
import shutil
import reduce_vars as web_var

from mantid.simpleapi import *

def main(input_file, output_dir):
    """ This is the (only) method required by the autoreduction interface. 
    
    input_file -- name of the input data file to reduce
    output_dir -- directory path to store file to
    
    To store files place use output_dir in combination with os.path.join() to
    to ensure that operating system dependent paths are handled correctly. For 
    example:
    
    fileToWriteTo = os.path.join(output_dir, "integrated.nxs")
    f = open(fileToWriteTo,"w")
    """
    
    logger.information("Save a dummy test file")
    fileToWriteTo = os.path.join(output_dir, "dummyTestFile.txt")
    f = open(fileToWriteTo,"w")
    f.write("Hello")
    f.close()    
    # shutil.copy(input_file, output_dir)
    
    # This is a just a message which should appear in reduction_log/#.log 
    # where # is the RB number
    print("Hello\n")
    
    print("Load data, integrate and save to output_dir")   
    ws = Load(input_file)
    ws = Integration(ws)
    SaveNexus(ws, os.path.join(output_dir, "integrated.nxs"))

    # Define additional custom folder to copy results to
    # Note this folder needs to be visible by the autoreduction system
    output_folder = ''    
    return output_folder

if __name__ == "__main__":
    main()
