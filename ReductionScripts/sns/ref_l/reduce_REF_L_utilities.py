"""
    Perform the stitching of a set of reflectivity curves from the Liquids Reflectometer at SNS.
    Most of this code was extracted from the REFL reduction UI.
"""
import os
import sys
import json
#sys.path.insert(0,'/opt/Mantid/bin')
sys.path.insert(0,'/opt/mantidnightly/bin')
import mantid
from mantid.simpleapi import *

def autoreduction_stitching(output_dir, first_run_of_set, endswith='auto', scale_to_unity=True, wl_cutoff=10.0):
    """
        Utility function used by the automated reduction to load 
        partial results and stitched them together.
        @param output_dir: directory where to put the final reflectivity file
        @param first_run_of_set: run number of the first run of the set
        @param endswith: optional parameter to add an identifier at the end of the saved files
    """
    for f in os.listdir(output_dir):
        if f.startswith("REFL_%s" % first_run_of_set) and f.endswith("%s.nxs" % endswith):
            ws_name = f.replace("_%s.nxs" % endswith, "")
            ws_name = ws_name.replace("REFL_", "")
            LoadNexus(Filename=os.path.join(output_dir, f), OutputWorkspace="reflectivity_%s_%s_ts" % (ws_name, endswith))

    ws_list = AnalysisDataService.getObjectNames()
    input_ws_list = []
    for ws in ws_list:
        if ws.endswith("%s_ts" % endswith):
            input_ws_list.append(ws)
            
    if len(input_ws_list) == 0:
        logger.notice("No data sets to stitch (%s)." % endswith)
        return False
    input_ws_list = sorted(input_ws_list)
    
    default_file_name = 'REFL_%s_combined_data_auto.txt' % first_run_of_set
    file_path = os.path.join(output_dir, default_file_name)
    _from_q = 0.005
    _bin_size = 0.02
    _bin_max = 2
    binning_parameters = "%g,-%g,%g" % (_from_q, _bin_size, _bin_max)
    LRReflectivityOutput(ReducedWorkspaces=input_ws_list, ScaleToUnity=scale_to_unity, ScalingWavelengthCutoff=wl_cutoff,
                         OutputBinning=binning_parameters, DQConstant=0.0004, DQSlope=0.025,
                         OutputFilename=file_path)
    return file_path
    
def selection_plots(workspace, output_dir, run_number):
    """
        Write the selection plot data to a file so that we can read it back and display it in the web monitor
    """
    n_x = int(workspace.getInstrument().getNumberParameter("number-of-x-pixels")[0])
    n_y = int(workspace.getInstrument().getNumberParameter("number-of-y-pixels")[0])

    peak_selection = RefRoi(InputWorkspace=workspace, NXPixel=n_x, NYPixel=n_y, IntegrateY=False, ConvertToQ=False)
    peak_selection = Transpose(InputWorkspace=peak_selection)
    lowres_selection = RefRoi(InputWorkspace=workspace, NXPixel=n_x, NYPixel=n_y, IntegrateY=True, ConvertToQ=False)
    lowres_selection = Transpose(InputWorkspace=lowres_selection)

    data = {}
    x = peak_selection.readX(0)
    y = peak_selection.readY(0)
    e = peak_selection.readE(0)
    data["peak_selection"] = {"x":list(x), "y":list(y), "e":list(e)}

    x = lowres_selection.readX(0)
    y = lowres_selection.readY(0)
    e = lowres_selection.readE(0)
    data["lowres_selection"] = {"x":list(x), "y":list(y), "e":list(e)}

    tof_dist = SumSpectra(InputWorkspace=workspace)
    tof_max =  workspace.getTofMax()
    tof_min =  workspace.getTofMin()
    tof_selection = Rebin(InputWorkspace=tof_dist, Params=[tof_min, 40, tof_max])
    x = tof_selection.readX(0)
    y = tof_selection.readY(0)
    e = tof_selection.readE(0)
    data["tof_selection"] = {"x":list(x), "y":list(y), "e":list(e)}

    #TODO: add the current selection ranges from the template
    json_data = json.dumps(data)
    
    fd = open(os.path.join(output_dir, "REF_L_%s_plot_data.dat" % run_number), 'w')
    fd.write(json_data)
    fd.close()

