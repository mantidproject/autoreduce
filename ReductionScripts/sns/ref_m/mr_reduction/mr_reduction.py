"""
    Reduction for MR
    
    #TODO: delete intermediate workspaces
"""
import sys
sys.path.insert(0,'/opt/mantidnightly/bin')
import mantid
from mantid.simpleapi import *
import numpy as np
import math
from scipy.optimize import curve_fit
import json
import time
import logging

from reflectivity_output import write_reflectivity
from data_info import DataInfo
from web_report import Report, process_collection

    
class ReductionProcess(object):
    tolerance=0.02
    
    def __init__(self, data_run, output_dir=None, const_q_binning=False, use_roi=True,
                 update_peak_range=False, use_roi_bck=False, use_tight_bck=False, bck_offset=3):
        """
            @param data_run: run number or file path
        """
        self.run_number = data_run
        self.ipts = None
        self.output_dir = output_dir
        self.const_q_binning = const_q_binning
        
        # Options
        self.use_roi = use_roi
        self.update_peak_range = update_peak_range
        self.use_roi_bck = use_roi_bck
        self.use_tight_bck = use_tight_bck
        self.bck_offset = bck_offset
        
        # Script for re-running the reduction
        self.script = ''
        
    def reduce(self):
        """
        """
        report_list = []

        # Reduce all cross-sections
        for entry in ['Off_Off', 'On_Off', 'Off_On', 'On_On']:
            try:
                report = self.reduce_cross_section(self.run_number, entry)
                report_list.append(report)
            except:
                # No data for this cross-section, skip to the next
                logging.info("Cross section %s: %s" % (entry, str(sys.exc_value)))

        # Generate stitched plot
        ref_plot = None
        try:
            from reflectivity_merge import combined_curves, plot_combined
            
            ipts_number = self.ipts.split('-')[1]
            matched_runs, scaling_factors = combined_curves(run=int(self.run_number), ipts=ipts_number)
            ref_plot = plot_combined(matched_runs, scaling_factors, ipts_number, publish=False)
        except:
            logging.error(str(sys.exc_value))

        # Generate report and script
        html_report, script = process_collection(summary_content=ref_plot, report_list=report_list, publish=True)

        try:
            if self.output_dir is None:
                self.output_dir = "/SNS/REF_M/%s/shared/autoreduce/" % self.ipts
            fd = open(os.path.join(self.output_dir, 'REF_M_%s_autoreduce.py' % self.run_number), 'w')
            fd.write(script)
            fd.close()
        except:
            logging.error("Could not write reduction script: %s" % sys.exc_value)
        return html_report

    def reduce_cross_section(self, run_number, entry='Off_Off'):
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
        self.ipts = ws.getRun().getProperty("experiment_identifier").value

        # Determine peak position and ranges
        data_info = DataInfo(ws, entry,
                             use_roi=self.use_roi,
                             update_peak_range=self.update_peak_range,
                             use_roi_bck=self.use_roi_bck,
                             use_tight_bck=self.use_tight_bck,
                             bck_offset=self.bck_offset)
        if data_info.data_type < 1:
            return Report(ws, data_info, data_info, None)

        # Find direct beam run
        norm_run = self.find_direct_beam(ws)
        if norm_run is None:
            logging.warning("Run %s [%s]: Could not find direct beam with matching slit, trying with wl only" % (run_number, entry))
            norm_run = self.find_direct_beam(ws, skip_slits=True)

        apply_norm = True
        direct_info = None
        if norm_run is None:
            logging.warning("Run %s [%s]: Could not find direct beam run: skipping" % (run_number, entry))
            apply_norm = False
        else:
            logging.info("Run %s [%s]: Direct beam run: %s" % (run_number, entry, norm_run))

            # Find peak in direct beam run
            for norm_entry in ['entry', 'entry-Off_Off', 'entry-On_Off', 'entry-Off_On', 'entry-On_On']:
                try:
                    ws_direct = LoadEventNexus(Filename="REF_M_%s" % norm_run,
                                               NXentryName=norm_entry,
                                               OutputWorkspace="MR_%s" % norm_run)
                    if ws_direct.getNumberEvents() > 10000:
                        logging.info("Found direct beam entry: %s [%s]" % (norm_run, norm_entry))
                        direct_info = DataInfo(ws_direct, norm_entry,
                                               use_roi=self.use_roi,
                                               update_peak_range=self.update_peak_range,
                                               use_roi_bck=self.use_roi_bck,
                                               use_tight_bck=self.use_tight_bck,
                                               bck_offset=self.bck_offset)
                        break
                except:
                    # No data in this cross-section
                    logging.debug("Direct beam %s: %s" % (norm_entry, sys.exc_value))

        if direct_info is None:
            direct_info = data_info

        MagnetismReflectometryReduction(RunNumbers=[run_number,],
                                        NormalizationRunNumber=norm_run,
                                        SignalPeakPixelRange=data_info.peak_range,
                                        SubtractSignalBackground=True,
                                        SignalBackgroundPixelRange=data_info.background,
                                        ApplyNormalization=apply_norm,
                                        NormPeakPixelRange=direct_info.peak_range,
                                        SubtractNormBackground=True,
                                        NormBackgroundPixelRange=direct_info.background,
                                        CutLowResDataAxis=True,
                                        LowResDataAxisPixelRange=data_info.low_res_range,
                                        CutLowResNormAxis=True,
                                        LowResNormAxisPixelRange=direct_info.low_res_range,
                                        CutTimeAxis=True,
                                        QMin=0.001,
                                        QStep=-0.01,
                                        UseWLTimeAxis=False,
                                        TimeAxisStep=40,
                                        UseSANGLE=True,
                                        TimeAxisRange=data_info.tof_range,
                                        SpecularPixel=data_info.peak_position,
                                        ConstantQBinning=self.const_q_binning,
                                        EntryName='entry-%s' % entry,
                                        OutputWorkspace="r_%s_%s" % (run_number, entry))

        # Write output file
        reflectivity = mtd["r_%s_%s" % (run_number, entry)]
        if self.output_dir is None:
            self.output_dir = "/SNS/REF_M/%s/shared/autoreduce/" % self.ipts
        write_reflectivity([mtd["r_%s_%s" % (run_number, entry)]],
                           os.path.join(self.output_dir, 'REF_M_%s_%s_autoreduce.dat' % (run_number, entry)), entry)

        return Report(ws, data_info, direct_info, mtd["r_%s_%s" % (run_number, entry)])

    def find_direct_beam(self, scatt_ws, skip_slits=False, allow_later_runs=False):
        """
            Find the appropriate direct beam run
        """
        data_dir = "/SNS/REF_M/%s/data" % self.ipts
        ar_dir = "/SNS/REF_M/%s/shared/autoreduce" % self.ipts

        wl_ = scatt_ws.getRun().getProperty("LambdaRequest").getStatistics().mean
        s1_ = scatt_ws.getRun().getProperty("S1HWidth").getStatistics().mean
        s2_ = scatt_ws.getRun().getProperty("S2HWidth").getStatistics().mean
        s3_ = scatt_ws.getRun().getProperty("S3HWidth").getStatistics().mean
        run_ = int(scatt_ws.getRunNumber())
        dangle_ = abs(scatt_ws.getRun().getProperty("DANGLE").getStatistics().mean)

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
                            logging.debug("Finding direct beam: %s [%s]: %s" % (item, entry, sys.exc_value))

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
                    data_info = DataInfo(ws, entry,
                                         use_roi=self.use_roi,
                                         update_peak_range=self.update_peak_range,
                                         use_roi_bck=self.use_roi_bck,
                                         use_tight_bck=self.use_tight_bck,
                                         bck_offset=self.bck_offset)
                    peak_pos = data_info.peak_position if data_info.peak_position is not None else direct_beam_pix
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
                #if run_number == run_ or (dangle > self.tolerance and huber_x < 9) :
                if run_number == run_ or ((theta_d > self.tolerance or sangle > self.tolerance) and huber_x < 4.95):
                    continue
                # If we don't allow runs taken later than the run we are processing...
                if not allow_later_runs and run_number > run_:
                    continue
                
                if math.fabs(wl-wl_) < self.tolerance \
                    and (skip_slits is True or \
                    (math.fabs(s1-s1_) < self.tolerance \
                    and math.fabs(s2-s2_) < self.tolerance \
                    and math.fabs(s3-s3_) < self.tolerance)):
                    if closest is None:
                        closest = run_number
                    elif abs(run_number-run_) < abs(closest-run_):
                        closest = run_number

        if closest is None:

            for item in os.listdir(ar_dir):
                if item.endswith(".json"):
                    summary_path = os.path.join(ar_dir, item)
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
                    #if run_number == run_ or (dangle > self.tolerance and huber_x < 9) :
                    if run_number == run_ or ((theta_d > self.tolerance or sangle > self.tolerance) and huber_x < 4.95):
                        continue
                    # If we don't allow runs taken later than the run we are processing...
                    if not allow_later_runs and run_number > run_:
                        continue
                    
                    if math.fabs(wl-wl_) < self.tolerance \
                        and (skip_slits is True or \
                        (math.fabs(s1-s1_) < self.tolerance \
                        and math.fabs(s2-s2_) < self.tolerance \
                        and math.fabs(s3-s3_) < self.tolerance)):
                        if closest is None:
                            closest = run_number
                        elif abs(run_number-run_) < abs(closest-run_):
                            closest = run_number

        return closest

