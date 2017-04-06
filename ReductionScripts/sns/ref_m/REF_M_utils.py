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

tolerance = 0.02
def reduce_data(run_number, use_roi=True):
    """
        Reduce a data run
        
        Return False if the data is a direct beam
    """
    all_plots = []
    for entry in ['Off_Off', 'On_Off', 'Off_On', 'On_On']:
        try:
            reflectivity, label = reduce_cross_section(run_number, entry, use_roi=use_roi)
            if reflectivity is None:
                logging.warning("No reflectivity for %s %s" % (run_number, entry))
                return False
            else:
                plots = report(run_number, entry, reflectivity)
                all_plots.append(plots)
        except:
            # No data for this cross-section, skip to the next
            logging.error(str(sys.exc_value))
            continue
    try:
        from REF_M_merge import combined_curves, plot_combined
        from postprocessing.publish_plot import publish_plot
        ipts_long = reflectivity.getRun().getProperty("experiment_identifier").value
        ipts = ipts_long.split('-')[1]
        matched_runs, scaling_factors = combined_curves(run=int(run_number), ipts=ipts)
        ref_plot = plot_combined(matched_runs, scaling_factors, ipts, publish=False)
        plot_html = "<div>%s</div>\n" % ref_plot
        for p in all_plots:
            plot_html += "<div>\n%s\n%s</div>" % (p[0], p[1])
        
        publish_plot("REF_M", run_number, files={'file': plot_html})
        
    except:
        logging.error(str(sys.exc_value))
        logging.error("No publisher module found")
        
    return True

def reduce_data_(run_number, use_roi=True):
    """
        Reduce a data run
        
        Return False if the data is a direct beam
    """
    data_list = []
    data_names = []
    for entry in ['Off_Off', 'On_Off', 'Off_On', 'On_On']:
        try:
            reflectivity, label = reduce_cross_section(run_number, entry, use_roi=use_roi)
            if reflectivity is None:
                logging.warning("No reflectivity for %s %s" % (run_number, entry))
                return False
            x = reflectivity.readX(0)
            y = reflectivity.readY(0)
            dy = reflectivity.readE(0)
            dx = reflectivity.readDx(0)
            data_list.append( [x, y, dy, dx] )
            data_names.append( label )
        except:
            # No data for this cross-section, skip to the next
            continue
    try:
        from postprocessing.publish_plot import plot1d
        if len(data_list) > 0:
            plot1d(run_number, data_list, data_names=data_names, instrument='REF_M',
                       x_title=u"Q (1/\u212b)", x_log=True,
                       y_title="Reflectivity", y_log=True, show_dx=False)
        else:
            logging.warning("Nothing to plot")
    except:
        logging.error(str(sys.exc_value))
        logging.error("No publisher module found")
        
    return True

def reduce_cross_section(run_number, entry='Off_Off', use_roi=True):
    """
        Reduce a given cross-section of a data run
    """
    # Find reflectivity peak of scattering run
    ws = LoadEventNexus(Filename="REF_M_%s" % run_number,
                        NXentryName='entry-%s' % entry,
                        OutputWorkspace="MR_%s" % run_number)
    scatt_peak, scatt_low_res, scatt_pos, is_direct = guess_params(ws, use_roi=use_roi)
    tof_range = get_tof_range(ws)

    # Find direct beam run
    norm_run = None
    if not is_direct:
        norm_run = find_direct_beam(ws)
        if norm_run is None:
            norm_run = find_direct_beam(ws, skip_slits=True)
    else:
        logging.info("This is a direct beam run")
        tof_min = ws.getTofMin()
        tof_max = ws.getTofMax()
        ws = Rebin(ws, Params="%s, 50, %s" % (tof_min, tof_max))
        ws = SumSpectra(ws)
        try:
            from postprocessing.publish_plot import plot1d
            x = ws.readX(0)
            y = ws.readY(0)
            dy = ws.readE(0)

            plot1d(run_number, [(x, y, dy),], data_names=['Direct Beam r%s' % run_number],
                   instrument='REF_M',
                   x_title=u"TOF", x_log=False,
                   y_title="Counts", y_log=True, show_dx=False)
        except:
            logging.error("No publisher module found")
        return None
        
    apply_norm = True
    if norm_run is None:
        logging.warning("Could not find direct beam run: skipping")
        apply_norm = False
        direct_peak = scatt_peak
        direct_low_res = scatt_low_res
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
                    direct_peak, direct_low_res, _, _ = guess_params(ws, use_roi=use_roi)
                    break
            except:
                # No data in this cross-section
                pass

    const_q_binning = False
    MagnetismReflectometryReduction(RunNumbers=[run_number,],
                                    NormalizationRunNumber=norm_run,
                                    SignalPeakPixelRange=scatt_peak,
                                    SubtractSignalBackground=True,
                                    SignalBackgroundPixelRange=[4, scatt_peak[0]-30],
                                    ApplyNormalization=apply_norm,
                                    NormPeakPixelRange=direct_peak,
                                    SubtractNormBackground=False,
                                    NormBackgroundPixelRange=[4, direct_peak[0]-30],
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
    return mtd["r_%s_%s" % (run_number, entry)], label

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
        
def find_direct_beam(scatt_ws, tolerance=0.02, skip_slits=False, allow_later_runs=False):
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
                dangle = ws.getRun().getProperty("DANGLE").getStatistics().mean
                huber_x = ws.getRun().getProperty("HuberX").getStatistics().mean
                wl = ws.getRun().getProperty("LambdaRequest").getStatistics().mean
                s1 = ws.getRun().getProperty("S1HWidth").getStatistics().mean
                s2 = ws.getRun().getProperty("S2HWidth").getStatistics().mean
                s3 = ws.getRun().getProperty("S3HWidth").getStatistics().mean
                meta_data = dict(run=run_number, wl=wl, s1=s1, s2=s2, s3=s3, dangle=dangle, huber_x=huber_x)
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
                wl = meta_data['wl']
                s1 = meta_data['s1']
                s2 = meta_data['s2']
                s3 = meta_data['s3']
                if 'huber_x' in meta_data:
                    huber_x = meta_data['huber_x']
                else:
                    huber_x = 0
            if run_number == run_ or (dangle > tolerance and huber_x < 9) :
                continue
            # If we don't allow runs taken later than the run we are processing...
            if not allow_later_runs and run_number > run_:
                continue
            
            if math.fabs(wl-wl_) < tolerance \
                and skip_slits is True or \
                (math.fabs(s1-s1_) < tolerance \
                and math.fabs(s2-s2_) < tolerance \
                and math.fabs(s3-s3_) < tolerance):
                if closest is None:
                    closest = run_number
                elif abs(run_number-run_) < abs(closest-run_):
                    closest = run_number

    return closest

def guess_params(ws, tolerance=0.02, use_roi=True):
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

    if use_roi and ws.getRun().hasProperty('ROI1StartX'):
        roi1_x0 = ws.getRun()['ROI1StartX'].getStatistics().mean
        roi1_y0 = ws.getRun()['ROI1StartY'].getStatistics().mean
        roi1_x1 = ws.getRun()['ROI1EndX'].getStatistics().mean
        roi1_y1 = ws.getRun()['ROI1EndY'].getStatistics().mean
        if roi1_x1 > roi1_x0:
            peak = [int(roi1_x0), int(roi1_x1)]
        else:
            peak = [int(roi1_x1), int(roi1_x0)]
        if roi1_y1 > roi1_y0:
            low_res = [int(roi1_y0), int(roi1_y1)]
        else:
            low_res = [int(roi1_y1), int(roi1_y0)]
    else:
        ws_low_res = RefRoi(InputWorkspace=ws, IntegrateY=False,
                               NXPixel=304, NYPixel=256,
                               ConvertToQ=False,
                               OutputWorkspace="ws_summed")

        integrated_low_res = Integration(ws_low_res)
        integrated_low_res = Transpose(integrated_low_res)

        # Find reflectivity peak
        peak, _, _ = LRPeakSelection(InputWorkspace=integrated)

        # Determine low-resolution region
        _, low_res, _ = LRPeakSelection(InputWorkspace=integrated_low_res)

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
    except:
        logging.warning("Could not use Gaussian fit to determine peak position")    
        #peak_position = np.average(signal_x_crop, weights=signal_y_crop)
        peak_position = (peak[1]+peak[0])/2.0

    peak = [int(peak[0]), int(peak[1])]
    low_res = [int(low_res[0]), int(low_res[1])]
    peak_position = float(peak_position)
    
    dangle_ = abs(ws.getRun().getProperty("DANGLE").getStatistics().mean)
    is_direct_beam = dangle_ < tolerance

    logging.warning("Run: %s [direct beam: %s]" % (ws.getRunNumber(), is_direct_beam))
    logging.warning("Peak position: %s" % peak_position)
    logging.warning("Reflectivity peak: %s" % str(peak))
    logging.warning("Low-resolution pixel range: %s" % str(low_res))
    return peak, low_res, peak_position, is_direct_beam

def write_reflectivity(ws_list, output_path, cross_section):
    # Sanity check
    if len(ws_list) == 0:
        return
        
    direct_beam_options=['DB_ID', 'P0', 'PN', 'x_pos', 'x_width', 'y_pos', 'y_width',
                         'bg_pos', 'bg_width', 'dpix', 'tth', 'number', 'File']
    dataset_options=['scale', 'P0', 'PN', 'x_pos', 'x_width', 'y_pos', 'y_width',
                     'bg_pos', 'bg_width', 'fan', 'dpix', 'tth', 'number', 'DB_ID', 'File']
    cross_sections={'Off_Off': '++', 'On_Off': '-+', 'Off_On': '+-', 'On_On': '--'}
    pol_state = 'x'
    if cross_section in cross_sections:
        pol_state = cross_sections[cross_section]

    fd = open(output_path, 'w')
    fd.write("# Datafile created by QuickNXS 1.0.32\n")
    fd.write("# Datafile created by Mantid %s\n" % mantid.__version__)
    fd.write("# Date: %s\n" % time.strftime(u"%Y-%m-%d %H:%M:%S"))
    fd.write("# Type: Specular\n")
    run_list = [str(ws.getRunNumber()) for ws in ws_list]
    fd.write("# Input file indices: %s\n" % ','.join(run_list))
    fd.write("# Extracted states: %s\n" % pol_state)
    fd.write("#\n")
    fd.write("# [Direct Beam Runs]\n")
    toks = ['%8s' % item for item in direct_beam_options]
    fd.write("# %s\n" % '  '.join(toks))

    # Direct beam section
    i_direct_beam = 0
    for ws in ws_list:
        i_direct_beam += 1
        run_object = ws.getRun()
        normalization_run = run_object.getProperty("normalization_run").value
        if normalization_run == "None":
            continue
        peak_min = run_object.getProperty("norm_peak_min").value
        peak_max = run_object.getProperty("norm_peak_max").value
        bg_min = run_object.getProperty("norm_bg_min").value
        bg_max = run_object.getProperty("norm_bg_max").value
        low_res_min = run_object.getProperty("norm_low_res_min").value
        low_res_max = run_object.getProperty("norm_low_res_max").value
        dpix = run_object.getProperty("normalization_dirpix").value
        filename = run_object.getProperty("normalization_file_path").value

        item = dict(DB_ID=i_direct_beam, tth=0, P0=0, PN=0,
                    x_pos=(peak_min+peak_max)/2.0,
                    x_width=peak_max-peak_min+1,
                    y_pos=(low_res_max+low_res_min)/2.0,
                    y_width=low_res_max-low_res_min+1,
                    bg_pos=(bg_min+bg_max)/2.0,
                    bg_width=bg_max-bg_min+1,
                    dpix=dpix,
                    number=normalization_run,
                    File=filename)

        par_list = ['{%s}' % p for p in direct_beam_options]
        template = "# %s\n" % '  '.join(par_list)
        _clean_dict = {}
        for key in item:
            if isinstance(item[key], (bool, str)):
                _clean_dict[key] = "%8s" % item[key]
            else:
                _clean_dict[key] = "%8g" % item[key]
        fd.write(template.format(**_clean_dict))

    # Scattering data
    fd.write("#\n") 
    fd.write("# [Data Runs]\n") 
    toks = ['%8s' % item for item in dataset_options]
    fd.write("# %s\n" % '  '.join(toks))
    i_direct_beam = 0
    for ws in ws_list:
        i_direct_beam += 1

        run_object = ws.getRun()
        peak_min = run_object.getProperty("scatt_peak_min").value
        peak_max = run_object.getProperty("scatt_peak_max").value
        bg_min = run_object.getProperty("scatt_bg_min").value
        bg_max = run_object.getProperty("scatt_bg_max").value
        low_res_min = run_object.getProperty("scatt_low_res_min").value
        low_res_max = run_object.getProperty("scatt_low_res_max").value
        dpix = run_object.getProperty("DIRPIX").getStatistics().mean
        filename = run_object.getProperty("Filename").value
        constant_q_binning = run_object.getProperty("constant_q_binning").value
        scatt_pos = run_object.getProperty("specular_pixel").value

        # For some reason, the tth value that QuickNXS expects is offset.
        # It seems to be because that same offset is applied later in the QuickNXS calculation.
        # Correct tth here so that it can load properly in QuickNXS and produce the same result.
        tth = run_object.getProperty("two_theta").value
        det_distance = run_object['SampleDetDis'].getStatistics().mean / 1000.0
        direct_beam_pix = run_object['DIRPIX'].getStatistics().mean

        # Get pixel size from instrument properties
        if ws.getInstrument().hasParameter("pixel_width"):
            pixel_width = float(ws.getInstrument().getNumberParameter("pixel_width")[0]) / 1000.0
        else:
            pixel_width = 0.0007
        tth -= ((direct_beam_pix - scatt_pos) * pixel_width) / det_distance * 180.0 / math.pi
        
        item = dict(scale=1, DB_ID=i_direct_beam, P0=0, PN=0, tth=tth,
                    fan=constant_q_binning,
                    x_pos=scatt_pos,
                    x_width=peak_max-peak_min+1,
                    y_pos=(low_res_max+low_res_min)/2.0,
                    y_width=low_res_max-low_res_min+1,
                    bg_pos=(bg_min+bg_max)/2.0,
                    bg_width=bg_max-bg_min+1,
                    dpix=dpix,
                    number=str(ws.getRunNumber()),
                    File=filename)

        par_list = ['{%s}' % p for p in dataset_options]
        template = "# %s\n" % '  '.join(par_list)
        _clean_dict = {}
        for key in item:
            if isinstance(item[key], str):
                _clean_dict[key] = "%8s" % item[key]
            else:
                _clean_dict[key] = "%8g" % item[key]
        fd.write(template.format(**_clean_dict))

    fd.write("#\n") 
    fd.write("# [Global Options]\n") 
    fd.write("# name           value\n")
    fd.write("# sample_length  10\n")
    fd.write("#\n") 
    fd.write("# [Data]\n") 
    toks = [u'%12s' % item for item in [u'Qz [1/A]', u'R [a.u.]', u'dR [a.u.]', u'dQz [1/A]', u'theta [rad]']]
    fd.write(u"# %s\n" % '  '.join(toks))
   
    for ws in ws_list:
        x = ws.readX(0)
        y = ws.readY(0)
        dy = ws.readE(0)
        dx = ws.readDx(0)
        tth = ws.getRun().getProperty("SANGLE").getStatistics().mean * math.pi / 180.0
        for i in range(len(x)):
            fd.write("%12.6g  %12.6g  %12.6g  %12.6g  %12.6g\n" % (x[i], y[i], dy[i], dx[i], tth))

    fd.close()
    
def _plot2d(x, y, z, x_range, y_range, x_label="X pixel", y_label="Y pixel"):
    colorscale=[[0, "rgb(0,0,131)"], [0.125, "rgb(0,60,170)"], [0.375, "rgb(5,255,255)"],
                [0.625, "rgb(255,255,0)"], [0.875, "rgb(250,0,0)"], [1, "rgb(128,0,0)"]]

    hm = go.Heatmap(x=x, y=y, z=z, autocolorscale=False, type='heatmap', showscale=False,
                     hoverinfo="none", colorscale=colorscale)

    data = [hm]
    if x_range is not None:
        x_left=go.Scatter(name='', x=[x_range[0], x_range[0]], y=[min(y), max(y)],
                          marker = dict(color = 'rgba(152, 0, 0, .8)',))
        x_right=go.Scatter(name='', x=[x_range[1], x_range[1]], y=[min(y), max(y)],
                           marker = dict(color = 'rgba(152, 0, 0, .8)',))
        data.append(x_left)
        data.append(x_right)
    
    if y_range is not None:
        y_left=go.Scatter(name='', y=[y_range[0], y_range[0]], x=[min(x), max(x)],
                          marker = dict(color = 'rgba(152, 0, 0, .8)',))
        y_right=go.Scatter(name='', y=[y_range[1], y_range[1]], x=[min(x), max(x)],
                           marker = dict(color = 'rgba(152, 0, 0, .8)',))
        data.append(y_left)
        data.append(y_right)
    
    x_layout = dict(title=x_label, zeroline=False, exponentformat="power",
                    showexponent="all", showgrid=True,
                    showline=True, mirror="all", ticks="inside")
    y_layout = dict(title=y_label, zeroline=False, exponentformat="power",
                    showexponent="all", showgrid=True,
                    showline=True, mirror="all", ticks="inside")
    layout = go.Layout(
        showlegend=False,
        autosize=True,
        width=400,
        height=400,
        margin=dict(t=40, b=40, l=40, r=40),
        hovermode='closest',
        bargap=0,
        xaxis=x_layout,
        yaxis=y_layout
    )
    fig = go.Figure(data=data, layout=layout)
    return py(fig, output_type='div', include_plotlyjs=False, show_link=False)

def report(run_number, entry, reflectivity=None):
    ws = LoadEventNexus(Filename="REF_M_%s" % run_number,
                        NXentryName='entry-%s' % entry,
                        OutputWorkspace="MR_%s" % run_number)
    n_x = int(ws.getInstrument().getNumberParameter("number-of-x-pixels")[0])
    n_y = int(ws.getInstrument().getNumberParameter("number-of-y-pixels")[0])

    if reflectivity is None:
        scatt_peak = None
        scatt_low_res = None
    else:
        run_object = reflectivity.getRun()
        scatt_peak = [run_object.getProperty("scatt_peak_min").value,
                      run_object.getProperty("scatt_peak_max").value]
        bg_min = run_object.getProperty("scatt_bg_min").value
        bg_max = run_object.getProperty("scatt_bg_max").value
        scatt_low_res = [run_object.getProperty("scatt_low_res_min").value,
                         run_object.getProperty("scatt_low_res_max").value]
        lambda_min = run_object.getProperty("lambda_min").value
        lambda_max = run_object.getProperty("lambda_max").value
        
    # X-Y plot
    signal = np.log10(mtd['MR_%s' % run_number].extractY())
    z=np.reshape(signal, (n_x, n_y))
    xy_plot = _plot2d(z=z.T, x=range(n_x), y=range(n_y), x_range=scatt_peak, y_range=scatt_low_res)

    # X-TOF plot
    tof_min = mtd['MR_%s' % run_number].getTofMin()
    tof_max = mtd['MR_%s' % run_number].getTofMax()
    ws = Rebin(mtd['MR_%s' % run_number], params="%s, 50, %s" % (tof_min, tof_max))

    direct_summed = RefRoi(InputWorkspace=ws, IntegrateY=True,
                           NXPixel=n_x, NYPixel=n_y,
                           ConvertToQ=False, YPixelMin=0, YPixelMax=n_y,
                           OutputWorkspace="direct_summed")
    signal = np.log10(direct_summed.extractY())
    tof_axis = direct_summed.extractX()[0]/1000.0

    x_tof_plot = _plot2d(z=signal, y=range(signal.shape[0]), x=tof_axis,
            x_range=None, y_range=scatt_peak,
            x_label="TOF (ms)", y_label="X pixel")
    return [xy_plot, x_tof_plot]

if __name__ == '__main__':
    reduce_data(sys.argv[1])

