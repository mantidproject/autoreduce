"""
    Autoreduction utilities for Mantid-based reduction.

    TODO: - Write output in a format that can be loaded in quicknxs
"""
import sys
#sys.path.insert(0,'/opt/mantidnightly/bin')
sys.path.insert(0,'/SNS/users/m2d/mantid_build/test/bin')
import mantid
from mantid.simpleapi import *
import numpy as np
import math
from scipy.optimize import curve_fit
import json
import logging

tolerance = 0.02
def reduce_data(run_number):
    """
        Reduce a data run
        
        Return False if the data is a direct beam
    """
    data_list = []
    data_names = []
    for entry in ['Off_Off', 'On_Off', 'Off_On', 'On_On']:
        try:
            reflectivity = reduce_cross_section(run_number, entry)
            if reflectivity is None:
                return False
            x = reflectivity.readX(0)
            y = reflectivity.readY(0)
            dy = reflectivity.readE(0)
            dx = reflectivity.readDx(0)
            data_list.append( (x, y, dy, dx) )
            data_names.append( entry )
        except:
            # No data for this cross-section, skip to the next
            continue

    try:
        from postprocessing.publish_plot import plot1d
        plot1d(run_number, data_list, data_names=data_names, instrument='REF_M',
                   x_title=u"Q (1/\u212b)", x_log=True,
                   y_title="Reflectivity", y_log=True, show_dx=False)
    except:
        logging.error(str(sys.exc_value))
        logging.error("No publisher module found")
        
    return True

def reduce_cross_section(run_number, entry='Off_Off'):
    """
        Reduce a given cross-section of a data run
    """
    # Find reflectivity peak of scattering run
    ws = LoadEventNexus(Filename="REF_M_%s" % run_number,
                        NXentryName='entry-%s' % entry,
                        OutputWorkspace="MR_%s" % run_number)
    scatt_peak, scatt_low_res, scatt_pos, is_direct = guess_params(ws)

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
        logging.info("Could not find direct beam run: skipping")
        apply_norm = False
        direct_peak = scatt_peak
        direct_low_res = scatt_low_res
    else:
        logging.info("Direct beam run: %s" % norm_run)

        # Find peak in direct beam run
        ws = LoadEventNexus(Filename="REF_M_%s" % norm_run,
                            NXentryName='entry-Off_Off',
                            OutputWorkspace="MR_%s" % norm_run)
        direct_peak, direct_low_res, _, _ = guess_params(ws)

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
                                    QMin=0.001,
                                    QStep=-0.01,
                                    UseWLTimeAxis=False,
                                    TimeAxisStep=40,
                                    UseSANGLE=True,
                                    #TimeAxisRange=[24000, 54000],
                                    SpecularPixel=scatt_pos,
                                    ConstantQBinning=False,
                                    EntryName='entry-Off_Off',
                                    OutputWorkspace="r_%s" % run_number)

    reflectivity = mtd["r_%s" % run_number]


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
    dangle_ = abs(scatt_ws.getRun().getProperty("DANGLE").getStatistics().mean)
    # Skip direct beam runs
    if dangle_ < tolerance:
        return None

    closest = None
    for item in os.listdir(data_dir):
        if item.endswith("_event.nxs") or item.endswith("h5"):
            summary_path = os.path.join(ar_dir, item+'.json')
            if not os.path.isfile(summary_path):
                try:
                    ws = LoadEventNexus(Filename=os.path.join(data_dir, item),
                                        NXentryName='entry-Off_Off',
                                        MetaDataOnly=True,
                                        OutputWorkspace="meta_data")
                except:
                    # If we can't load the Off-Off entry, it's not a direct beam
                    meta_data = dict(run=0, invalid=True)
                    fd = open(summary_path, 'w')
                    fd.write(json.dumps(meta_data))
                    fd.close()
                    continue
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
                if 'invalid' in meta_data.keys():
                    continue
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

def guess_params(ws, tolerance=0.02):
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
    
    dangle_ = abs(ws.getRun().getProperty("DANGLE").getStatistics().mean)
    is_direct_beam = dangle_ < tolerance

    logging.warning("Run: %s [direct beam: %s]" % (ws.getRunNumber(), is_direct_beam))
    logging.warning("Peak position: %s" % peak_position)
    logging.warning("Reflectivity peak: %s" % str(peak))
    logging.warning("Low-resolution pixel range: %s" % str(low_res))
    return peak, low_res, peak_position, is_direct_beam

if __name__ == '__main__':
    reduce_data(sys.argv[1])

