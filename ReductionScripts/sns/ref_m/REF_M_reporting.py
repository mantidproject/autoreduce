"""
    Autoreduction utilities for Mantid-based reduction.
    Reporting and plotting.
"""
import sys
sys.path.insert(0,'/opt/mantidnightly/bin')
import mantid
from mantid.simpleapi import *
import numpy as np
import math
import json
import time
import logging
import plotly.offline as py
import plotly.graph_objs as go

def write_reflectivity(ws_list, output_path, cross_section):
    """
        Write out reflectivity output
    """
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
    
    data_block = ''
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
        norm_x_min = run_object.getProperty("norm_peak_min").value
        norm_x_max = run_object.getProperty("norm_peak_max").value
        norm_y_min = run_object.getProperty("norm_low_res_min").value
        norm_y_max = run_object.getProperty("norm_low_res_max").value

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
        
        x = ws.readX(0)
        y = ws.readY(0)
        dy = ws.readE(0)
        dx = ws.readDx(0)
        tth = ws.getRun().getProperty("SANGLE").getStatistics().mean * math.pi / 180.0
        quicknxs_scale = (float(norm_x_max)-float(norm_x_min)) * (float(norm_y_max)-float(norm_y_min))
        quicknxs_scale /= (float(peak_max)-float(peak_min)) * (float(low_res_max)-float(low_res_min))
        quicknxs_scale *= 0.005 / math.sin(tth)
        for i in range(len(x)):
            data_block += "%12.6g  %12.6g  %12.6g  %12.6g  %12.6g\n" % (x[i], y[i]*quicknxs_scale, dy[i]*quicknxs_scale, dx[i], tth)

    fd.write("#\n") 
    fd.write("# [Global Options]\n") 
    fd.write("# name           value\n")
    fd.write("# sample_length  10\n")
    fd.write("#\n") 
    fd.write("# [Data]\n") 
    toks = [u'%12s' % item for item in [u'Qz [1/A]', u'R [a.u.]', u'dR [a.u.]', u'dQz [1/A]', u'theta [rad]']]
    fd.write(u"# %s\n" % '  '.join(toks))
    fd.write(u"# %s\n" % data_block)

    fd.close()
    
def _plot2d(x, y, z, x_range, y_range, x_label="X pixel", y_label="Y pixel", title=''):
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
        title=title,
        showlegend=False,
        autosize=True,
        width=300,
        height=300,
        margin=dict(t=40, b=40, l=40, r=20),
        hovermode='closest',
        bargap=0,
        xaxis=x_layout,
        yaxis=y_layout
    )
    fig = go.Figure(data=data, layout=layout)
    return py.plot(fig, output_type='div', include_plotlyjs=False, show_link=False)

def _plot1d(x, y, x_range=None, x_label='', y_label="Counts", title=''):

    data = [go.Scatter(name='', x=x, y=y)]

    if x_range is not None:
        min_y = min([v for v in y if v>0])
        x_left=go.Scatter(name='', x=[x_range[0], x_range[0]], y=[min_y, max(y)],
                          marker = dict(color = 'rgba(152, 0, 0, .8)',))
        x_right=go.Scatter(name='', x=[x_range[1], x_range[1]], y=[min_y, max(y)],
                           marker = dict(color = 'rgba(152, 0, 0, .8)',))
        data.append(x_left)
        data.append(x_right)

    x_layout = dict(title=x_label, zeroline=False, exponentformat="power",
                    showexponent="all", showgrid=True,
                    showline=True, mirror="all", ticks="inside")

    y_layout = dict(title=y_label, zeroline=False, exponentformat="power",
                    showexponent="all", showgrid=True, type='log',
                    showline=True, mirror="all", ticks="inside")

    layout = go.Layout(
        title=title,
        showlegend=False,
        autosize=True,
        width=300,
        height=300,
        margin=dict(t=40, b=40, l=40, r=20),
        hovermode='closest',
        bargap=0,
        xaxis=x_layout,
        yaxis=y_layout
    )

    fig = go.Figure(data=data, layout=layout)
    return py.plot(fig, output_type='div', include_plotlyjs=False, show_link=False)

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
        
    # X-Y plot
    signal = np.log10(mtd['MR_%s' % run_number].extractY())
    z=np.reshape(signal, (n_x, n_y))
    xy_plot = _plot2d(z=z.T, x=range(n_x), y=range(n_y),
                      x_range=scatt_peak, y_range=scatt_low_res,
                      title="r%s [%s]" % (run_number, entry))

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
                         x_label="TOF (ms)", y_label="X pixel",
                         title="r%s [%s]" % (run_number, entry))
                         
    # Count per X pixel
    integrated = Integration(direct_summed)
    integrated = Transpose(integrated)
    signal_y = integrated.readY(0)
    signal_x = range(len(signal_y))
    peak_pixels = _plot1d(signal_x,signal_y, x_range=scatt_peak,
                          x_label="X pixel", y_label="Counts",
                          title="r%s [%s]" % (run_number, entry))

    # TOF distribution
    ws = SumSpectra(ws)
    signal_x = ws.readX(0)/1000.0
    signal_y = ws.readY(0)
    tof_dist = _plot1d(signal_x,signal_y, x_range=None,
                       x_label="TOF (ms)", y_label="Counts",
                       title="r%s [%s]" % (run_number, entry))

    ipts_long = ws.getRun().getProperty("experiment_identifier").value
    return [xy_plot, x_tof_plot, peak_pixels, tof_dist], ipts_long

def get_meta_data(ws, use_roi=True):
    """
        TODO: add the run number of the direct beam
    """
    if ws is None:
        return ''
    run_object = ws.getRun()
    constant_q_binning = run_object['constant_q_binning'].value
    sangle = run_object['SANGLE'].getStatistics().mean
    dangle = run_object['DANGLE'].getStatistics().mean
    lambda_min = run_object['lambda_min'].value
    lambda_max = run_object['lambda_max'].value
    theta = run_object['two_theta'].value / 2
    huber_x = run_object["HuberX"].getStatistics().mean
    direct_beam = run_object["normalization_run"].value

    dangle0 = run_object['DANGLE0'].getStatistics().mean
    dirpix = run_object['DIRPIX'].getStatistics().mean
    
    peak = [run_object['scatt_peak_min'].value,
            run_object['scatt_peak_max'].value]

    bg = [run_object['scatt_bg_min'].value,
          run_object['scatt_bg_max'].value]

    low_res = [run_object['scatt_low_res_min'].value,
               run_object['scatt_low_res_max'].value]

    specular_pixel = run_object['specular_pixel'].value

    roi1_x0 = int(ws.getRun()['ROI1StartX'].getStatistics().mean)
    roi2_x0 = int(ws.getRun()['ROI2StartX'].getStatistics().mean)
    roi1_x1 = int(ws.getRun()['ROI1EndX'].getStatistics().mean)
    roi2_x1 = int(ws.getRun()['ROI2EndX'].getStatistics().mean)

    meta = "<table style='width:40%'>"
    meta += "<tr><td>Run:</td><td><b>%s</b></td></tr>" % run_object['run_number'].value
    meta += "<tr><td>Direct beam:</td><td>%s</td></tr>" % direct_beam
    meta += "<tr><td>Q-binning:</td><td>%s</td></tr>" % constant_q_binning
    meta += "<tr><td>Using ROI:</td><td>%s</td></tr>" % use_roi
    meta += "<tr><td>Specular peak:</td><td>%g</td></tr>" % specular_pixel
    meta += "<tr><td>Peak range:</td><td>%s - %s</td></tr>" % (peak[0], peak[1])
    meta += "<tr><td>Background:</td><td>%s - %s</td></tr>" % (bg[0], bg[1])
    meta += "<tr><td>Low-res range:</td><td>%s - %s</td></tr><tr>" % (low_res[0], low_res[1])
    meta += "<tr><td>ROI 1:</td><td>%s - %s</td></tr><tr>" % (min(roi1_x0, roi1_x1), max(roi1_x0, roi1_x1))
    meta += "<tr><td>ROI 2:</td><td>%s - %s</td></tr><tr>" % (min(roi2_x0, roi2_x1), max(roi2_x0, roi2_x1))
    meta += "</table>\n"
    
    meta += "<p><table style='width:100%'>"
    meta += "<tr><th>Theta</th><th>DANGLE</th><th>SANGLE</th><th>DIRPIX</th><th>Wavelength</th><th>Huber X</th></tr>"
    meta += "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s - %s</td><td>%s</td></tr>\n" % (theta, dangle, sangle, dirpix, lambda_min, lambda_max, huber_x)
    meta += "</table>\n"
    return meta
    

