"""
    Perform the stitching of a set of reflectivity curves from the Liquids Reflectometer at SNS.
    Most of this code was extracted from the REFL reduction UI.
"""
import os
import sys
import json
sys.path.insert(0,'/opt/mantidnightly/bin')
import mantid
from mantid.simpleapi import *

sys.path.append("/opt/mantidnightly/scripts/")
from LargeScaleStructures.data_stitching import DataSet, Stitcher

def create_ascii_file(first_run_of_set, scaled_ws_list, output_dir):
    """
        Create an ASCII file with the stitched reflectivity.

        This code was/is part of the REFL UI.

        @param first_run_of_set: first run of a set of runs to be stitched
        @param scaled_ws_list: list of scaled workspaces to combine
        @param output_dir: output directory for the reflectivity file
    """
    dq0 = 0.0009
    dq_over_q = 0.045
    content = '#dQ0[1/Angstrom]=%g\n' % dq0
    content += '#dQ/Q=%g\n' % dq_over_q
    content += '#Q(1/Angstrom) R delta_R Precision\n'

    # Average points at the same Q and produce the final reflectivity
    wks_file_name = average_points_for_single_q(first_run_of_set, scaled_ws_list)

    x_axis = mtd[wks_file_name].readX(0)
    y_axis = mtd[wks_file_name].readY(0)
    e_axis = mtd[wks_file_name].readE(0)

    for i in range(len(x_axis)-1):
        # do not display data where R=0
        if (y_axis[i] > 1e-15):
            content += str(x_axis[i])
            content += ' ' + str(y_axis[i])
            content += ' ' + str(e_axis[i])
            _precision = str(dq0 + dq_over_q * x_axis[i])
            content += ' ' + _precision
            content += '\n'

    default_file_name = 'REFL_%s_combined_data.txt' % first_run_of_set
    file_path = os.path.join(output_dir, default_file_name)
    f=open(file_path,'w')
    f.write(content)
    f.close()

def average_points_for_single_q(first_run_of_set, scaled_ws_list):
    """
        Take the point with the smalled error when multiple points are
        at the same q-value.

        This code was/is part of the REFL UI.

        @param first_run_of_set: first run of a set of runs to be stitched
        @param scaled_ws_list: list of scaled workspaces to combine
    """
    from numpy import NAN

    # Get binning parameters
    _from_q = 0.005
    _bin_size = 0.01
    _bin_max = 2
    binning_parameters = "%g,-%g,%g" % (_from_q, _bin_size, _bin_max)

    file_number = 0
    for ws in scaled_ws_list:
        data_y = mtd[ws].dataY(0)
        data_e = mtd[ws].dataE(0)

        # cleanup data 0-> NAN
        for j in range(len(data_y)):
            if data_y[j] < 1e-12:
                data_y[j] = NAN
                data_e[j] = NAN

        file_number = file_number + 1

    # Convert each histo to histograms and rebin to final binning
    for ws in scaled_ws_list:
        new_name = "%s_histo" % ws
        ConvertToHistogram(InputWorkspace=ws, OutputWorkspace=new_name)
        Rebin(InputWorkspace=new_name, Params=binning_parameters,
              OutputWorkspace=new_name)

    # Take the first rebinned histo as our output
    data_y = mtd[scaled_ws_list[0]+'_histo'].dataY(0)
    data_e = mtd[scaled_ws_list[0]+'_histo'].dataE(0)

    # Skip first 3 points and last one
    skip_index = 0
    point_to_skip = 3
    # Add in the other histos, averaging the overlaps
    for i in range(1, len(scaled_ws_list)): 
        skip_point = True
        can_skip_last_point = False

        data_y_i = mtd[scaled_ws_list[i]+'_histo'].dataY(0)
        data_e_i = mtd[scaled_ws_list[i]+'_histo'].dataE(0)
        for j in range(len(data_y_i)-1):
            if data_y_i[j] > 0:
                can_skip_last_point = True
                if skip_point:
                    skip_index = skip_index + 1
                    if skip_index == point_to_skip:
                        skip_point = False
                        skip_index = 0
                    else:
                        continue

            if can_skip_last_point and (data_y_i[j+1]==0):
                break

            # Take the data that has the smallest error
            if data_y[j]>0 and data_y_i[j]>0:
                if (data_e[j] > data_e_i[j]):
                    data_y[j] = data_y_i[j]
                    data_e[j] = data_e_i[j]
            elif (data_y[j] == 0) and (data_y_i[j]>0):
                data_y[j] = data_y_i[j]
                data_e[j] = data_e_i[j]

    return scaled_ws_list[0]+'_histo'

def create_single_reflectivity(workspace_list, scale_to_unity=True,
                               max_q_unity = 0.01, endswith="auto"):
    """
        Create a single reflectivity curve out of several reduced data sets.
        @param workspace_list: list of scaled workspaces to combine
        @param scale_to_unity: if True, the critical edge will be normalized to 1
        @param endswith: optional parameter to add an identifier at the end of the saved files
    """
    if len(workspace_list) == 0:
        raise RuntimeError, "Create_single_reflectivity was called with an empty workspace list"
    
    # Check whether all data sets have absolute normalization available
    normalization_available = True
    for ws in workspace_list:
        if mtd[ws].getRun().hasProperty("isSFfound"):
            if mtd[ws].getRun().getProperty("isSFfound").value == 'False':
                try:
                    wl = mtd[ws].getRun().getProperty("LambdaRequest").value[0]
                    # We don't care about the scaling factor for wl > 10 A
                    normalization_available = wl>10.0
                except:
                    logger.notice("Could not find LambdaRequest for %s" % ws)  
                    normalization_available = False
        else:
            normalization_available = False

    # Prepare the data sets
    s = Stitcher()

    # Keep track of overall normalization
    global_normalization = 1.0
    
    for i in range(len(workspace_list)):
        item = workspace_list[i]
        data = DataSet(item)
        data.load(True, False)
        s.append(data)

        # Scale to unity as needed
        if i==0 and scale_to_unity:
            try:  
                global_normalization = data.scale_to_unity(0.0, max_q_unity)
            except:
                logger.notice("Could not scale to unity for %s" % item)
        data.set_scale(global_normalization)

    # Set the reference data (index of the data set in the workspace list)
    s.set_reference(0)
    if normalization_available == False:
        logger.notice("Absolute normalization not available: stitching")
        s.compute()

    # Now that we have the scaling factors computed, simply apply them
    scaled_ws_list = []
    for i in range(len(workspace_list)):
        d = s.get_data_set(i)
        xmin, xmax = d.get_skipped_range()
        d.apply_scale(xmin, xmax)
        scaled_ws_list.append(d.get_scaled_ws())

    # Create combined output
    s.get_scaled_data(workspace="reflectivity_%s" % endswith)
    return scaled_ws_list, normalization_available

def autoreduction_stitching(output_dir, first_run_of_set, endswith='auto'):
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
    
    scaled_ws_list, has_normalization = create_single_reflectivity(input_ws_list, endswith=endswith)
    
    create_ascii_file(first_run_of_set, scaled_ws_list, output_dir)
    
    # Remove workspaces we created
    for item in scaled_ws_list:
        if AnalysisDataService.doesExist(item):
            AnalysisDataService.remove(item)
    logger.notice("Has normalization (%s)? %s" % (endswith, has_normalization))
    return has_normalization

def selection_plots(workspace, output_dir, run_number):
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

    json_data = json.dumps(data)
    
    fd = open(os.path.join(output_dir, "REF_L_%s_plot_data.dat" % run_number), 'w')
    fd.write(json_data)
    fd.close()

if __name__ == '__main__':
    autoreduction_stitching('/SNS/REF_L/IPTS-11804/shared/autoreduce/', 124391, 'auto')
