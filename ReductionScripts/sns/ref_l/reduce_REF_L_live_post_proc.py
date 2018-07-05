import sys
import mantid.simpleapi as api
import numpy as np

import plotly.offline as py
import plotly.graph_objs as go

def _plot2d(x, y, z, x_range=None, y_range=None, x_label="X pixel", y_label="Y pixel", title='', x_bck_range=None, y_bck_range=None):
    """
        Generate a 2D plot
        :param array x: x-axis values
        :param array y: y-axis values
        :param array z: z-axis counts
        :param str x_label: x-axis label
        :param str y_label: y-axis label
        :param str title: plot title
        :param array x_bck_range: array of length 2 to specify a background region in x
        :param array y_bck_range: array of length 2 to specify a background region in y
    """
    colorscale=[[0, "rgb(0,0,131)"], [0.125, "rgb(0,60,170)"], [0.375, "rgb(5,255,255)"],
                [0.625, "rgb(255,255,0)"], [0.875, "rgb(250,0,0)"], [1, "rgb(128,0,0)"]]

    heatmap = go.Heatmap(x=x, y=y, z=z, autocolorscale=False, type='heatmap', showscale=False,
                         hoverinfo="none", colorscale=colorscale)

    data = [heatmap]
    if x_range is not None:
        x_left=go.Scatter(name='', x=[x_range[0], x_range[0]], y=[min(y), max(y)],
                          marker = dict(color = 'rgba(152, 0, 0, .8)',))
        x_right=go.Scatter(name='', x=[x_range[1], x_range[1]], y=[min(y), max(y)],
                           marker = dict(color = 'rgba(152, 0, 0, .8)',))
        data.append(x_left)
        data.append(x_right)

    if x_bck_range is not None:
        x_left=go.Scatter(name='', x=[x_bck_range[0], x_bck_range[0]], y=[min(y), max(y)],
                          marker = dict(color = 'rgba(152, 152, 152, .8)',))
        x_right=go.Scatter(name='', x=[x_bck_range[1], x_bck_range[1]], y=[min(y), max(y)],
                           marker = dict(color = 'rgba(152, 152, 152, .8)',))
        data.append(x_left)
        data.append(x_right)

    if y_range is not None:
        y_left=go.Scatter(name='', y=[y_range[0], y_range[0]], x=[min(x), max(x)],
                          marker = dict(color = 'rgba(152, 0, 0, .8)',))
        y_right=go.Scatter(name='', y=[y_range[1], y_range[1]], x=[min(x), max(x)],
                           marker = dict(color = 'rgba(152, 0, 0, .8)',))
        data.append(y_left)
        data.append(y_right)

    if y_bck_range is not None:
        y_left=go.Scatter(name='', y=[y_bck_range[0], y_bck_range[0]], x=[min(x), max(x)],
                          marker = dict(color = 'rgba(152, 152, 152, .8)',))
        y_right=go.Scatter(name='', y=[y_bck_range[1], y_bck_range[1]], x=[min(x), max(x)],
                           marker = dict(color = 'rgba(152, 152, 152, .8)',))
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

def _plot1d(x, y, x_range=None, x_label='', y_label="Counts", title='', bck_range=None):
    """
        Generate a simple 1D plot
        :param array x: x-axis values
        :param array y: y-axis values
        :param str x_label: x-axis label
        :param str y_label: y-axis label
        :param str title: plot title
        :param array bck_range: array of length 2 to specify a background region in x
    """
    data = [go.Scatter(name='', x=x, y=y)]

    if x_range is not None:
        min_y = min([v for v in y if v>0])
        x_left=go.Scatter(name='', x=[x_range[0], x_range[0]], y=[min_y, max(y)],
                          marker = dict(color = 'rgba(152, 0, 0, .8)',))
        x_right=go.Scatter(name='', x=[x_range[1], x_range[1]], y=[min_y, max(y)],
                           marker = dict(color = 'rgba(152, 0, 0, .8)',))
        data.append(x_left)
        data.append(x_right)

    if bck_range is not None:
        min_y = min([v for v in y if v>0])
        x_left=go.Scatter(name='', x=[bck_range[0], bck_range[0]], y=[min_y, max(y)],
                          marker = dict(color = 'rgba(152, 152, 152, .8)',))
        x_right=go.Scatter(name='', x=[bck_range[1], bck_range[1]], y=[min_y, max(y)],
                           marker = dict(color = 'rgba(152, 152, 152, .8)',))
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

def reduce_data(ws):
    output_dir = "/SNS/REF_L/IPTS-18965/shared/autoreduce"
    # Locate the template file
    # If no template file is available, the automated reduction will generate one
    template_file = ""
    if os.path.isfile("template.xml"):
        template_file = "template.xml"
    elif os.path.isfile(os.path.join(output_dir, "template.xml")):
        template_file = os.path.join(output_dir, "template.xml")
    elif os.path.isfile("/SNS/REF_L/shared/autoreduce/template.xml"):
        template_file = "/SNS/REF_L/shared/autoreduce/template.xml"
    
    # Reduction options
    #-------------------------------------------------------------------------
    # Wavelength below which we don't need the absolute normalization
    WL_CUTOFF = 10.0  

    # Default primary fraction range to be used if it is not defined in the template
    PRIMARY_FRACTION_RANGE = [116, 197]

    NORMALIZE_TO_UNITY = False

    output = LRAutoReduction(#Filename=event_file_path,
                             InputWorkspace=ws,
                             ScaleToUnity=NORMALIZE_TO_UNITY,
                             ScalingWavelengthCutoff=WL_CUTOFF,
                             PrimaryFractionRange=PRIMARY_FRACTION_RANGE,
                             OutputDirectory=output_dir,
                             SlitTolerance=0.06,
                             ReadSequenceFromFile=True,
                             OrderDirectBeamsByRunNumber=True,
                             TemplateFile=template_file, FindPeaks=False)
    first_run_of_set=int(output[1])


    #-------------------------------------------------------------------------
    # Produce plot for the web monitor
    default_file_name = 'REFL_%s_combined_data_auto.txt' % first_run_of_set
    if os.path.isfile(default_file_name):
        print("Loading %s" % os.path.join(output_dir, default_file_name))
        reflectivity = LoadAscii(Filename=os.path.join(output_dir, default_file_name), Unit="MomentumTransfer")

        return reflectivity



def generate_plots(run_number, workspace):
    """
        Generate diagnostics plots
    """
    n_x = int(workspace.getInstrument().getNumberParameter("number-of-x-pixels")[0])
    n_y = int(workspace.getInstrument().getNumberParameter("number-of-y-pixels")[0])

    # X-TOF plot
    tof_min = workspace.getTofMin()
    tof_max = workspace.getTofMax()
    workspace = api.Rebin(workspace, params="%s, 50, %s" % (tof_min, tof_max))

    direct_summed = api.RefRoi(InputWorkspace=workspace, IntegrateY=False,
                           NXPixel=n_x, NYPixel=n_y,
                           ConvertToQ=False, YPixelMin=0, YPixelMax=n_y,
                           OutputWorkspace="direct_summed")
    signal = np.log10(direct_summed.extractY())
    tof_axis = direct_summed.extractX()[0]/1000.0

    x_tof_plot = _plot2d(z=signal, y=range(signal.shape[0]), x=tof_axis,
                         x_label="TOF (ms)", y_label="Y pixel",
                         title="r%s" % run_number)

    # X-Y plot
    _workspace = api.Integration(workspace)
    signal = np.log10(_workspace.extractY())
    z=np.reshape(signal, (n_x, n_y))
    xy_plot = _plot2d(z=z.T, x=np.arange(n_x), y=np.arange(n_y),
                      title="r%s" % run_number)

    # Count per X pixel
    integrated = api.Integration(direct_summed)
    integrated = api.Transpose(integrated)
    signal_y = integrated.readY(0)
    signal_x = range(len(signal_y))
    peak_pixels = _plot1d(signal_x,signal_y,
                          x_label="Y pixel", y_label="Counts",
                          title="r%s" % run_number)

    # TOF distribution
    workspace = api.SumSpectra(workspace)
    signal_x = workspace.readX(0)/1000.0
    signal_y = workspace.readY(0)
    tof_dist = _plot1d(signal_x,signal_y, x_range=None,
                       x_label="TOF (ms)", y_label="Counts",
                       title="r%s" % run_number)

    return [xy_plot, x_tof_plot, peak_pixels, tof_dist]
    
output = input
try:
    run_number = input.getRunNumber()
except:
    run_number = 0

refl_info = ""
try:
    refl = reduce_data(input)
    x = reflectivity.readX(0)
    y = reflectivity.readY(0)
    refl_info = _plot1d(x, y, x_range=None,
                       x_label="Q", y_label="R",
                       title="r%s" % run_number)
except:
    refl_info = "<div>Could not reduce data: %s</div>\n" % sys.exc_value

plots = generate_plots(run_number, input)
info = ''
try:
    n_evts = input.getNumberEvents()
    seq_number = input.getRun()['sequence_number'].value[0]
    seq_total = input.getRun()['sequence_total'].value[0]
    info = "<div>Events: %s</div>\n" % n_evts
    info += "<div>Sequence: %s of %s</div>\n" % (seq_number, seq_total) 
except:
    info = "<div>Error: %s</div>\n" % sys.exc_value

plot_html = "<div>Live data</div>\n"
plot_html += info
plot_html += refl_info
plot_html += "<table style='width:100%'>\n"
plot_html += "<tr>\n"
for plot in plots:
    plot_html += "<td>%s</td>\n" % plot
plot_html += "</tr>\n"
plot_html += "</table>\n"
plot_html += "<hr>\n"

mantid.logger.information('Posting plot of run %s' % run_number)
try: # version on autoreduce
    from postprocessing.publish_plot import publish_plot
except ImportError: # version on instrument computers
    from finddata import publish_plot
request = publish_plot('REF_L', run_number, files={'file':plot_html})
mantid.logger.information("post returned %d" % request.status_code)

