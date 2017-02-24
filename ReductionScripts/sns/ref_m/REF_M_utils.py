"""
    Autoreduction utilities for Mantid-based reduction.

    TODO: - Write output in a format that can be loaded in quicknxs
"""
import sys
sys.path.insert(0,'/opt/mantidnightly/bin')
import mantid
from mantid.simpleapi import *
import numpy as np
import math
from scipy.optimize import curve_fit
import json
import logging

def reduce_data(run_number):
    """
        Reduce a data run
    """
    # Find reflectivity peak of scattering run
    ws = LoadEventNexus(Filename="REF_M_%s" % run_number,
                        NXentryName='entry-Off_Off',
                        OutputWorkspace="MR_%s" % run_number)
    scatt_peak, scatt_low_res, scatt_pos = guess_params(ws)

    # Find direct beam run
    norm_run = find_direct_beam(ws)
    if norm_run is None:
        norm_run = find_direct_beam(ws, skip_slits=True)
        
    apply_norm = True
    if norm_run is None:
        logging.notice("Could not find direct beam run: skipping")
        apply_norm = False
    else:
        logging.notice("Direct beam run: %s" % norm_run)

    # Find peak in direct beam run
    ws = LoadEventNexus(Filename="REF_M_%s" % norm_run,
                        NXentryName='entry-Off_Off',
                        OutputWorkspace="MR_%s" % norm_run)
    direct_peak, direct_low_res, _ = guess_params(ws)

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
                                    CutTimeAxis=False,
                                    QMin=0.005,
                                    QStep=-0.01,
                                    UseWLTimeAxis=False,
                                    TimeAxisStep=40,
                                    #TimeAxisRange=[24000, 54000],
                                    SpecularPixel=scatt_pos,
                                    ConstantQBinning=False,
                                    EntryName='entry-Off_Off',
                                    OutputWorkspace="r_%s" % run_number)

    try:
        from postprocessing.publish_plot import plot1d
        reflectivity = mtd["r_%s" % run_number]
        x = reflectivity.readX(0)
        y = reflectivity.readY(0)
        dy = reflectivity.readE(0)
        dx = reflectivity.readDx(0)

        plot1d(run_number, [[x, y, dy, dx]], instrument='REF_M',
                   x_title=u"Q (1/\u212b)", x_log=True,
                   y_title="Reflectivity", y_log=True, show_dx=False)
    except:
        logging.error("No publisher module found")

    return reflectivity

def find_direct_beam(scatt_ws, tolerance=0.02, skip_slits=False):
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

    closest = None
    for item in os.listdir(data_dir):
        if item.endswith("_event.nxs") or item.endswith("h5"):
            summary_path = os.path.join(ar_dir, item+'.json')
            if not os.path.isfile(summary_path):
                ws = LoadEventNexus(Filename=os.path.join(data_dir, item),
                                    NXentryName='entry-Off_Off',
                                    MetaDataOnly=True,
                                    OutputWorkspace="meta_data")
                run_number = int(ws.getRunNumber())
                dangle = ws.getRun().getProperty("DANGLE").getStatistics().mean
                wl = ws.getRun().getProperty("LambdaRequest").getStatistics().mean
                s1 = ws.getRun().getProperty("S1HWidth").getStatistics().mean
                s2 = ws.getRun().getProperty("S2HWidth").getStatistics().mean
                s3 = ws.getRun().getProperty("S3HWidth").getStatistics().mean
                meta_data = dict(run=run_number, wl=wl, s1=s1, s2=s2, s3=s3, dangle=dangle)
                fd = open(summary_path, 'w')
                fd.write(json.dumps(meta_data))
                fd.close()
            else:
                fd = open(summary_path, 'r')
                meta_data = json.loads(fd.read())
                fd.close()
                run_number = meta_data['run']
                dangle = meta_data['dangle']
                wl = meta_data['wl']
                s1 = meta_data['s1']
                s2 = meta_data['s2']
                s3 = meta_data['s3']
            if run_number == run_ or dangle > tolerance:
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

def guess_params(ws):
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
    coeff, var_matrix = curve_fit(gauss, signal_x_crop, signal_y_crop, p0=p0)

    #peak_position = np.average(signal_x_crop, weights=signal_y_crop)
    peak_position = coeff[1]

    peak = [int(peak[0]), int(peak[1])]
    low_res = [int(low_res[0]), int(low_res[1])]
    peak_position = float(peak_position)
    return peak, low_res, peak_position

if __name__ == '__main__':
    reduce_data(sys.argv[1])

