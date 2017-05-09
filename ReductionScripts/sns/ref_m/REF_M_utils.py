"""
    Autoreduction utilities for Mantid-based reduction.

    TODO: - Write output in a format that can be loaded in quicknxs
"""
import sys
sys.path.insert(0,'/opt/mantidnightly/bin')
#sys.path.insert(0,'/SNS/users/m2d/mantid_build/test/bin')
import mantid
from mantid.simpleapi import *
import numpy as np
import math
from scipy.optimize import curve_fit
import json
import time
import logging
import plotly.offline as py
import plotly.graph_objs as go

from REF_M_reporting import get_meta_data, report, _plot1d, _plot2d, write_reflectivity

tolerance = 0.02
def reduce_data(run_number, use_roi=True):
    """
        Reduce a data run
        
        Return False if the data is a direct beam
    """
    all_plots = []
    reflectivity = None
    ipts_long = ''
    script = '# This script was automatically generated\n'
    script += '# Reduction time: %s\n' % time.ctime()
    for entry in ['Off_Off', 'On_Off', 'Off_On', 'On_On']:
        try:
            reflectivity, type_info = reduce_cross_section(run_number, entry, use_roi=use_roi)
            #if reflectivity is not None:
            #    ipts_long = reflectivity.getRun().getProperty("experiment_identifier").value
            if reflectivity is None and type_info == -1:
                logging.warning("No reflectivity for %s %s" % (run_number, entry))
                script += "# No reflectivity for %s %s\n" % (run_number, entry)
                continue
            else:
                plots, ipts_long = report(run_number, entry, reflectivity)
                all_plots.append(plots)
                if reflectivity is not None:
                    script_text = GeneratePythonScript(reflectivity)
                    script += '# Run:%s    Cross-section: %s\n' % (run_number, entry)
                    script += script_text.replace(', ',',\n                                ')
                    script += '\n'
        except:
            # No data for this cross-section, skip to the next
            try:
                plots, ipts_long = report(run_number, entry, None)
                all_plots.append(plots)
            except:
                # No data for this cross-section
                logging.error("No data for diagnostics for %s" % entry)
            logging.error(str(sys.exc_value))

    try:
        output_dir = "/SNS/REF_M/%s/shared/autoreduce/" % ipts_long
        fd = open(os.path.join(output_dir, 'REF_M_%s_autoreduce.py' % run_number), 'w')
        fd.write(script)
        fd.close()
    except:
        logging.error("Could not write reduction script: %s" % sys.exc_value)

    if len(all_plots) == 0:
        return False
    try:
        from REF_M_merge import combined_curves, plot_combined
        from postprocessing.publish_plot import publish_plot
        
        ipts = ipts_long.split('-')[1]
        if reflectivity is not None:
            matched_runs, scaling_factors = combined_curves(run=int(run_number), ipts=ipts)
            ref_plot = plot_combined(matched_runs, scaling_factors, ipts, publish=False)
        else:
            ref_plot = None
        plot_html = ''
        if ref_plot is not None:
            plot_html += "<div>%s</div>\n" % ref_plot
        meta_div = get_meta_data(reflectivity, use_roi=use_roi)
        if meta_div is not None:
            plot_html += "<div>%s</div>\n" % meta_div
        plot_html += "<table style='width:100%'>\n"
        for p in all_plots:
            plot_html += "<tr><td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td></tr>" % (p[0], p[1], p[2], p[3])
        plot_html += "</table>\n"
        publish_plot("REF_M", run_number, files={'file': plot_html})

    except:
        logging.error(str(sys.exc_value))
        logging.error("No publisher module found")
        
    return True

def reduce_cross_section(run_number, entry='Off_Off', use_roi=True):
    """
        Reduce a given cross-section of a data run
        Returns a reflectivity workspace and an information value
        
        Type info:
            -1: too few counts
             0: direct beam run
             1: scattering run
    """
    # Find reflectivity peak of scattering run
    ws = LoadEventNexus(Filename="REF_M_%s" % run_number,
                        NXentryName='entry-%s' % entry,
                        OutputWorkspace="MR_%s" % run_number)
    if ws.getNumberEvents() < 10000:
        return None, -1
    scatt_peak, scatt_low_res, scatt_pos, is_direct, bck_range = guess_params(ws, use_roi=use_roi)
    tof_range = get_tof_range(ws)

    # Find direct beam run
    norm_run = None
    if not is_direct:
        norm_run = find_direct_beam(ws, peak_position=scatt_pos)
        if norm_run is None:
            norm_run = find_direct_beam(ws, skip_slits=True, peak_position=scatt_pos)
    else:
        logging.info("This is a direct beam run")
        return None, 0
        
    apply_norm = True
    if norm_run is None:
        logging.warning("Could not find direct beam run: skipping")
        apply_norm = False
        direct_peak = scatt_peak
        direct_low_res = scatt_low_res
        direct_bck = bck_range
    else:
        logging.warning("Direct beam run: %s" % norm_run)

        # Find peak in direct beam run
        for norm_entry in ['entry', 'entry-Off_Off', 'entry-On_Off', 'entry-Off_On', 'entry-On_On']:
            try:
                ws = LoadEventNexus(Filename="REF_M_%s" % norm_run,
                                NXentryName=norm_entry,
                                OutputWorkspace="MR_%s" % norm_run)
                if ws.getNumberEvents() > 10000:
                    logging.warning("Found direct beam entry: %s" % norm_entry)
                    direct_peak, direct_low_res, _, _, direct_bck = guess_params(ws, use_roi=use_roi)
                    logging.warning("Direct beam signal: peak=%s low=%s " % (direct_peak, direct_low_res))
                    break
            except:
                # No data in this cross-section
                logging.error("Direct beam %s: %s" % (norm_entry, sys.exc_value))

    const_q_binning = False
    MagnetismReflectometryReduction(RunNumbers=[run_number,],
                                    NormalizationRunNumber=norm_run,
                                    SignalPeakPixelRange=scatt_peak,
                                    SubtractSignalBackground=True,
                                    SignalBackgroundPixelRange=bck_range,
                                    ApplyNormalization=apply_norm,
                                    NormPeakPixelRange=direct_peak,
                                    SubtractNormBackground=False,
                                    NormBackgroundPixelRange=direct_bck,
                                    CutLowResDataAxis=True,
                                    LowResDataAxisPixelRange=scatt_low_res,
                                    CutLowResNormAxis=True,
                                    LowResNormAxisPixelRange=direct_low_res,
                                    CutTimeAxis=True,
                                    QMin=0.001,
                                    QStep=-0.01,
                                    UseWLTimeAxis=False,
                                    TimeAxisStep=40,
                                    UseSANGLE=True,
                                    TimeAxisRange=tof_range,
                                    SpecularPixel=scatt_pos,
                                    ConstantQBinning=const_q_binning,
                                    EntryName='entry-%s' % entry,
                                    OutputWorkspace="r_%s_%s" % (run_number, entry))

    # Write output file
    reflectivity = mtd["r_%s_%s" % (run_number, entry)]
    ipts = reflectivity.getRun().getProperty("experiment_identifier").value
    output_dir = "/SNS/REF_M/%s/shared/autoreduce/" % ipts
    write_reflectivity([mtd["r_%s_%s" % (run_number, entry)]],
                       os.path.join(output_dir, 'REF_M_%s_%s_autoreduce.dat' % (run_number, entry)), entry)
    
    label = entry
    if not apply_norm:
        label += " [no direct beam]"
    return mtd["r_%s_%s" % (run_number, entry)], 1

def get_tof_range(workspace):
        """
            Determine TOF range from the data
        """
        run_object = workspace.getRun()
        sample_detector_distance = run_object['SampleDetDis'].getStatistics().mean / 1000.0
        source_sample_distance = run_object['ModeratorSamDis'].getStatistics().mean / 1000.0
        source_detector_distance = source_sample_distance + sample_detector_distance
        
        h = 6.626e-34  # m^2 kg s^-1
        m = 1.675e-27  # kg
        wl = run_object.getProperty('LambdaRequest').value[0]
        chopper_speed = run_object.getProperty('SpeedRequest1').value[0]
        wl_offset = 0
        cst = source_detector_distance / h * m
        tof_min = cst * (wl + wl_offset * 60.0 / chopper_speed - 1.4 * 60.0 / chopper_speed) * 1e-4
        tof_max = cst * (wl + wl_offset * 60.0 / chopper_speed + 1.4 * 60.0 / chopper_speed) * 1e-4
        return [tof_min, tof_max]

def scattering_angle(ws, peak_position=None):
    dangle = ws.getRun().getProperty("DANGLE").getStatistics().mean
    dangle0 = ws.getRun().getProperty("DANGLE0").getStatistics().mean
    direct_beam_pix = ws.getRun().getProperty("DIRPIX").getStatistics().mean
    det_distance = ws.getRun().getProperty("SampleDetDis").getStatistics().mean / 1000.0
    pixel_width = 0.0007

    peak_pos = peak_position if peak_position is not None else direct_beam_pix
    theta_d = (dangle - dangle0) / 2.0
    theta_d += ((direct_beam_pix - peak_pos) * pixel_width) * 180.0 / math.pi / (2.0 * det_distance)
    
    return theta_d

def check_direct_beam(ws, peak_position=None):
    huber_x = ws.getRun().getProperty("HuberX").getStatistics().mean
    dangle = ws.getRun().getProperty("DANGLE").getStatistics().mean
    sangle = ws.getRun().getProperty("SANGLE").getStatistics().mean
    theta_d = scattering_angle(ws, peak_position)
    return not ((theta_d > tolerance or sangle > tolerance) and huber_x < 4.95)

def find_direct_beam(scatt_ws, tolerance=0.02, skip_slits=False, allow_later_runs=False, peak_position=None):
    """
        Find the appropriate direct beam run
    """
    ipts = scatt_ws.getRun().getProperty("experiment_identifier").value
    data_dir = "/SNS/REF_M/%s/data" % ipts
    ar_dir = "/SNS/REF_M/%s/shared/autoreduce" % ipts

    wl_ = scatt_ws.getRun().getProperty("LambdaRequest").getStatistics().mean
    s1_ = scatt_ws.getRun().getProperty("S1HWidth").getStatistics().mean
    s2_ = scatt_ws.getRun().getProperty("S2HWidth").getStatistics().mean
    s3_ = scatt_ws.getRun().getProperty("S3HWidth").getStatistics().mean
    run_ = int(scatt_ws.getRunNumber())
    dangle_ = abs(scatt_ws.getRun().getProperty("DANGLE").getStatistics().mean)
    # Skip direct beam runs
    if dangle_ < tolerance:
        return None

    closest = None
    for item in os.listdir(data_dir):
        if item.endswith("_event.nxs") or item.endswith("h5"):
            summary_path = os.path.join(ar_dir, item+'.json')
            if not os.path.isfile(summary_path):
                is_valid = False
                for entry in ['entry', 'entry-Off_Off', 'entry-On_Off', 'entry-Off_On', 'entry-On_On']:
                    try:
                        ws = LoadEventNexus(Filename=os.path.join(data_dir, item),
                                            NXentryName=entry,
                                            MetaDataOnly=False,
                                            OutputWorkspace="meta_data")
                        if ws.getNumberEvents() > 1000:
                            is_valid = True
                            break
                    except:
                        # If there's no data in the entry, LoadEventNexus will fail.
                        # This is expected so we just need to proceed with the next entry.
                        pass

                if not is_valid:
                    meta_data = dict(run=0, invalid=True)
                    fd = open(summary_path, 'w')
                    fd.write(json.dumps(meta_data))
                    fd.close()
                    continue

                run_number = int(ws.getRunNumber())
                sangle = ws.getRun().getProperty("SANGLE").getStatistics().mean
                dangle = ws.getRun().getProperty("DANGLE").getStatistics().mean
                dangle0 = ws.getRun().getProperty("DANGLE0").getStatistics().mean
                direct_beam_pix = ws.getRun().getProperty("DIRPIX").getStatistics().mean
                det_distance = ws.getRun().getProperty("SampleDetDis").getStatistics().mean / 1000.0
                pixel_width = 0.0007

                huber_x = ws.getRun().getProperty("HuberX").getStatistics().mean
                wl = ws.getRun().getProperty("LambdaRequest").getStatistics().mean
                s1 = ws.getRun().getProperty("S1HWidth").getStatistics().mean
                s2 = ws.getRun().getProperty("S2HWidth").getStatistics().mean
                s3 = ws.getRun().getProperty("S3HWidth").getStatistics().mean
                peak_pos = peak_position if peak_position is not None else direct_beam_pix
                theta_d = (dangle - dangle0) / 2.0
                theta_d += ((direct_beam_pix - peak_pos) * pixel_width) * 180.0 / math.pi / (2.0 * det_distance)

                meta_data = dict(theta_d=theta_d, run=run_number, wl=wl, s1=s1, s2=s2, s3=s3, dangle=dangle, sangle=sangle, huber_x=huber_x)
                fd = open(summary_path, 'w')
                fd.write(json.dumps(meta_data))
                fd.close()
            else:
                fd = open(summary_path, 'r')
                meta_data = json.loads(fd.read())
                fd.close()
                if 'invalid' in meta_data.keys():
                    continue
                run_number = meta_data['run']
                dangle = meta_data['dangle']
                theta_d = meta_data['theta_d'] if 'theta_d' in meta_data else 0
                sangle = meta_data['sangle'] if 'sangle' in meta_data else 0

                wl = meta_data['wl']
                s1 = meta_data['s1']
                s2 = meta_data['s2']
                s3 = meta_data['s3']
                if 'huber_x' in meta_data:
                    huber_x = meta_data['huber_x']
                else:
                    huber_x = 0
            #if run_number == run_ or (dangle > tolerance and huber_x < 9) :
            if run_number == run_ or ((theta_d > tolerance or sangle > tolerance) and huber_x < 4.95):
                continue
            # If we don't allow runs taken later than the run we are processing...
            if not allow_later_runs and run_number > run_:
                continue
            
            if math.fabs(wl-wl_) < tolerance \
                and (skip_slits is True or \
                (math.fabs(s1-s1_) < tolerance \
                and math.fabs(s2-s2_) < tolerance \
                and math.fabs(s3-s3_) < tolerance)):
                if closest is None:
                    closest = run_number
                elif abs(run_number-run_) < abs(closest-run_):
                    closest = run_number

    return closest

def process_roi(ws):
    # Read ROI 1
    roi1_valid = True
    roi1_x0 = ws.getRun()['ROI1StartX'].getStatistics().mean
    roi1_y0 = ws.getRun()['ROI1StartY'].getStatistics().mean
    roi1_x1 = ws.getRun()['ROI1EndX'].getStatistics().mean
    roi1_y1 = ws.getRun()['ROI1EndY'].getStatistics().mean
    if roi1_x1 > roi1_x0:
        peak1 = [int(roi1_x0), int(roi1_x1)]
    else:
        peak1 = [int(roi1_x1), int(roi1_x0)]
    if roi1_y1 > roi1_y0:
        low_res1 = [int(roi1_y0), int(roi1_y1)]
    else:
        low_res1 = [int(roi1_y1), int(roi1_y0)]
    if peak1 == [0,0] and low_res1 == [0,0]:
        roi1_valid = False

    # Read ROI 2
    roi2_valid = True
    roi2_x0 = ws.getRun()['ROI2StartX'].getStatistics().mean
    roi2_y0 = ws.getRun()['ROI2StartY'].getStatistics().mean
    roi2_x1 = ws.getRun()['ROI2EndX'].getStatistics().mean
    roi2_y1 = ws.getRun()['ROI2EndY'].getStatistics().mean
    if roi2_x1 > roi2_x0:
        peak2 = [int(roi2_x0), int(roi2_x1)]
    else:
        peak2 = [int(roi2_x1), int(roi2_x0)]
    if roi2_y1 > roi2_y0:
        low_res2 = [int(roi2_y0), int(roi2_y1)]
    else:
        low_res2 = [int(roi2_y1), int(roi2_y0)]
    if peak2 == [0,0] and low_res2 == [0,0]:
        roi2_valid = False

    # Pick the ROI that describes the reflectivity peak
    if roi1_valid and not roi2_valid:
        return peak1, low_res1, None
    elif roi2_valid and not roi1_valid:
        return peak2, low_res2, None
    elif roi1_valid and roi2_valid:
        # If ROI 2 is within ROI 1, treat it as the peak,
        # otherwise, use ROI 1
        if peak1[0] >= peak2[0] and peak1[1] <= peak2[1]:
            return peak1, low_res1, peak2
        elif peak2[0] >= peak1[0] and peak2[1] <= peak1[1]:
            return peak2, low_res2, peak1
        return peak1, low_res1, None

    return None, None, None

def determine_low_res_range(ws, offset=50):
    ws_low_res = RefRoi(InputWorkspace=ws, IntegrateY=False,
                           NXPixel=304, NYPixel=256,
                           ConvertToQ=False,
                           OutputWorkspace="ws_summed")

    integrated_low_res = Integration(ws_low_res)
    integrated_low_res = Transpose(integrated_low_res)

    # Determine low-resolution region
    x_values = integrated_low_res.readX(0)
    y_values = integrated_low_res.readY(0)
    e_values = integrated_low_res.readE(0)
    ws_short = CreateWorkspace(DataX=x_values[offset:200], DataY=y_values[offset:200], DataE=e_values[offset:200])
    _, low_res, _ = LRPeakSelection(InputWorkspace=ws_short)
    low_res = [low_res[0]+offset, low_res[1]+offset]
    return low_res
        
def guess_params(ws, tolerance=0.02, use_roi=True, fit_within_roi=False, find_bck=False):
    """
        Determine peak positions
    """
    ws_summed = RefRoi(InputWorkspace=ws, IntegrateY=True,
                           NXPixel=304, NYPixel=256,
                           ConvertToQ=False,
                           OutputWorkspace="ws_summed")

    integrated = Integration(ws_summed)
    integrated = Transpose(integrated)
    signal_y = integrated.readY(0)
    signal_x = range(len(signal_y))
    
    # Find reflectivity peak
    offset = 50
    x_values = integrated.readX(0)
    y_values = integrated.readY(0)
    e_values = integrated.readE(0)
    ws_short = CreateWorkspace(DataX=x_values[offset:210], DataY=y_values[offset:210], DataE=e_values[offset:210])
    _peak, _, _ = LRPeakSelection(InputWorkspace=ws_short)
    _peak = [_peak[0]+offset, _peak[1]+offset]
        
    _low_res = determine_low_res_range(ws)
    roi_valid = use_roi
    bck_range = None

    if use_roi:
        peak, low_res, bck_range = process_roi(ws)
        roi_valid = peak is not None
    
    if not roi_valid:
        peak = _peak
        low_res = _low_res

    # Determine reflectivity peak position (center)
    signal_y_crop = signal_y[peak[0]:peak[1]+1]
    signal_x_crop = signal_x[peak[0]:peak[1]+1]

    def gauss(x, *p):
        A, mu, sigma = p
        return A*np.exp(-(x-mu)**2/(2.*sigma**2))
    p0 = [np.max(signal_y), (peak[1]+peak[0])/2.0, (peak[1]-peak[0])/2.0]
    try:
        coeff, var_matrix = curve_fit(gauss, signal_x_crop, signal_y_crop, p0=p0)
        peak_position = coeff[1]
        peak_width = 3.0*coeff[2]
    except:
        logging.warning("Could not use Gaussian fit to determine peak position")    
        #peak_position = np.average(signal_x_crop, weights=signal_y_crop)
        try:
            coeff, var_matrix = curve_fit(gauss, signal_x, signal_y, p0=p0)
            peak_position = coeff[1]
            peak_width = 3.0*coeff[2]
            peak = _peak
            low_res = [5, 250]
            fit_within_roi = True
            logging.warning("Peak not in supplied range! Found peak: %s low: %s" % (peak, low_res))
        except:
            logging.warning("Could not use Gaussian fit to determine peak position over whole detector")    
            peak_position = (peak[1]+peak[0])/2.0
            peak_width = (peak[1]-peak[0])/2.0

    peak_position = float(peak_position)
    if fit_within_roi:
        peak[0] = math.floor(peak_position-peak_width)
        peak[1] = math.ceil(peak_position+peak_width)

    peak = [int(peak[0]), int(peak[1])]
    low_res = [int(low_res[0]), int(low_res[1])]
    
    #TODO: replace this
    dangle_ = abs(ws.getRun().getProperty("DANGLE").getStatistics().mean)
    is_direct_beam = check_direct_beam(ws, peak_position)# dangle_ < tolerance

    logging.warning("Run: %s [direct beam: %s]" % (ws.getRunNumber(), is_direct_beam))
    logging.warning("Peak position: %s" % peak_position)
    logging.warning("Reflectivity peak: %s" % str(peak))
    logging.warning("Low-resolution pixel range: %s" % str(low_res))
    
    if not find_bck or bck_range is None:
        bck_range = [4, peak[0]-30]
    return peak, low_res, peak_position, is_direct_beam, bck_range

if __name__ == '__main__':
    reduce_data(sys.argv[1])

