"""
    Reduction for MR
"""
import sys
sys.path.insert(0,'/opt/mantidnightly/bin')
import mantid
from mantid.simpleapi import *
import numpy as np
import math
from scipy.optimize import curve_fit
import logging
    
class DataInfo(object):
    """
        Class to hold the relevant information from a run (scattering or direct beam).
    """
    n_x_pixel = 304
    n_y_pixel = 256
    peak_range_offset = 50
    tolerance = 0.02
    pixel_width = 0.0007
    n_events_cutoff = 10000
    huber_x_cut = 4.95
    
    def __init__(self, ws, cross_section, use_roi=True, update_peak_range=False, use_roi_bck=False,
                 use_tight_bck=False, bck_offset=3, huber_x_cut=4.95,
                 force_peak_roi=False, peak_roi=[0,0],
                 force_bck_roi=False, bck_roi=[0,0]):
        self.cross_section = cross_section
        self.run_number = ws.getRunNumber()
        self.is_direct_beam = False
        self.data_type = 1
        self.peak_position = 0
        self.huber_x_cut = huber_x_cut
        self.peak_range = [0,0]
        self.low_res_range = [0,0]
        self.background = [0,0]
        
        # ROI information
        self.roi_peak = [0,0]
        self.roi_low_res = [0,0]
        self.roi_background = [0,0]

        # Options to override the ROI
        self.force_peak_roi = force_peak_roi
        self.forced_peak_roi = peak_roi
        self.force_bck_roi = force_bck_roi
        self.forced_bck_roi = bck_roi
        
        # Peak found before fitting for the central position
        self.found_peak = [0,0]
        self.found_low_res = [0,0]

        # Processing options
        # Use the ROI rather than finding the ranges
        self.use_roi = use_roi
        self.use_roi_actual = False

        # Use the 2nd ROI as the background, if available
        self.use_roi_bck = use_roi_bck
        self.use_tight_bck = use_tight_bck
        self.bck_offset = bck_offset

        # Update the specular peak range after finding the peak
        # within the ROI
        self.update_peak_range = update_peak_range

        self.get_tof_range(ws)
        self.determine_data_type(ws)
        
    def log(self):
        logging.info("| Run: %s [direct beam: %s]" % (self.run_number, self.is_direct_beam))
        logging.info("|   Peak position: %s" % self.peak_position)
        logging.info("|   Reflectivity peak: %s" % str(self.peak_range))
        logging.info("|   Low-resolution pixel range: %s" % str(self.low_res_range))

    def get_tof_range(self, ws):
            """
                Determine TOF range from the data
            """
            run_object = ws.getRun()
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
            
            self.tof_range = [tof_min, tof_max]
            return [tof_min, tof_max]
        
    def process_roi(self, ws):
        """
            Process the ROI information and determine the peak
            range, the low-resolution range, and the background range.
        """
        self.roi_peak = [0,0]
        self.roi_low_res = [0,0]
        self.roi_background = [0,0]

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
            self.roi_peak = peak1
            self.roi_low_res = low_res1
            self.roi_background = [0,0]
        elif roi2_valid and not roi1_valid:
            self.roi_peak = peak2
            self.roi_low_res = low_res2
            self.roi_background = [0,0]
        elif roi1_valid and roi2_valid:
            # If ROI 2 is within ROI 1, treat it as the peak,
            # otherwise, use ROI 1
            if peak1[0] >= peak2[0] and peak1[1] <= peak2[1]:
                self.roi_peak = peak1
                self.roi_low_res = low_res1
                self.roi_background = peak2
            elif peak2[0] >= peak1[0] and peak2[1] <= peak1[1]:
                self.roi_peak = peak2
                self.roi_low_res = low_res2
                self.roi_background = peak1
            else:
                self.roi_peak = peak1
                self.roi_low_res = low_res1
                self.roi_background = [0,0]

        # After all this, update the ROI according to reduction options
        if self.force_peak_roi:
            self.roi_peak = self.forced_peak_roi
        if self.force_bck_roi:
            self.roi_background = self.forced_bck_roi

    def determine_peak_range(self, ws, specular=True, max_pixel=230):
        ws_summed = RefRoi(InputWorkspace=ws, IntegrateY=specular,
                           NXPixel=self.n_x_pixel, NYPixel=self.n_y_pixel,
                           ConvertToQ=False,
                           OutputWorkspace="ws_summed")

        integrated = Integration(ws_summed)
        integrated = Transpose(integrated)

        x_values = integrated.readX(0)
        y_values = integrated.readY(0)
        e_values = integrated.readE(0)
        ws_short = CreateWorkspace(DataX=x_values[self.peak_range_offset:max_pixel],
                                   DataY=y_values[self.peak_range_offset:max_pixel],
                                   DataE=e_values[self.peak_range_offset:max_pixel])
        try:
            specular_peak, low_res, _ = LRPeakSelection(InputWorkspace=ws_short)
        except:
            logging.error("Peak finding error [specular=%s]: %s" % (specular, sys.exc_value))
            
            return integrated, [0,0]
        if specular:
            peak = [specular_peak[0]+self.peak_range_offset, specular_peak[1]+self.peak_range_offset]
        else:
            # The low-resolution range finder tends to be a bit tight.
            # Broaden it by a third.
            #TODO: Fix the range finder algorithm
            broadening = (low_res[1]-low_res[0])/3.0
            peak = [low_res[0]+self.peak_range_offset-broadening,
                    low_res[1]+self.peak_range_offset+broadening]
        return integrated, peak
    
    @classmethod
    def fit_peak(cls, signal_x, signal_y, peak):
        def gauss(x, *p):
            A, mu, sigma = p
            return A*np.exp(-(x-mu)**2/(2.*sigma**2))

        p0 = [np.max(signal_y), (peak[1]+peak[0])/2.0, (peak[1]-peak[0])/2.0]
        coeff, var_matrix = curve_fit(gauss, signal_x, signal_y, p0=p0)
        peak_position = coeff[1]
        peak_width = math.fabs(3.0*coeff[2])
        return peak_position, peak_width

    @classmethod
    def scattering_angle(cls, ws, peak_position=None):
        """
            Determine the scattering angle
        """
        dangle = ws.getRun().getProperty("DANGLE").getStatistics().mean
        dangle0 = ws.getRun().getProperty("DANGLE0").getStatistics().mean
        direct_beam_pix = ws.getRun().getProperty("DIRPIX").getStatistics().mean
        det_distance = ws.getRun().getProperty("SampleDetDis").getStatistics().mean / 1000.0

        peak_pos = peak_position if peak_position is not None else direct_beam_pix
        theta_d = (dangle - dangle0) / 2.0
        theta_d += ((direct_beam_pix - peak_pos) * cls.pixel_width) * 180.0 / math.pi / (2.0 * det_distance)
        return theta_d

    def check_direct_beam(self, ws, peak_position=None):
        """
            Determine whether this data is a direct beam
        """
        huber_x = ws.getRun().getProperty("HuberX").getStatistics().mean
        dangle = ws.getRun().getProperty("DANGLE").getStatistics().mean
        sangle = ws.getRun().getProperty("SANGLE").getStatistics().mean
        self.theta_d = self.scattering_angle(ws, peak_position)
        return not ((self.theta_d > self.tolerance or sangle > self.tolerance) and huber_x < self.huber_x_cut)

    def determine_data_type(self, ws):
        """
            Inspect the data and determine peak locations
            and data type.
        """
        # Skip empty data entries
        if ws.getNumberEvents() < self.n_events_cutoff:
            self.data_type = -1
            logging.info("No data for %s %s" % (self.run_number, self.cross_section))
            return

        # Find reflectivity peak and low resolution ranges
        # Those will be our defaults
        integrated, peak = self.determine_peak_range(ws, specular=True)
        self.found_peak = peak
        logging.info("Run %s [%s]: Peak found %s" % (self.run_number, self.cross_section, peak))
        signal_y = integrated.readY(0)
        signal_x = range(len(signal_y))
        _, low_res = self.determine_peak_range(ws, specular=False)
        self.found_low_res = low_res
        bck_range = None
        
        # Process the ROI information
        self.process_roi(ws)

        # Keep track of whether we actually used the ROI
        self.use_roi_actual = False
        
        if self.use_roi and self.roi_peak is not None:
            peak = self.roi_peak
            low_res = self.roi_low_res
            bck_range = self.roi_background
            self.use_roi_actual = True

        # Determine reflectivity peak position (center)
        signal_y_crop = signal_y[peak[0]:peak[1]+1]
        signal_x_crop = signal_x[peak[0]:peak[1]+1]

        peak_position = (peak[1]+peak[0])/2.0
        peak_width = (peak[1]-peak[0])/2.0
        try:
            # Try to find the peak position within the peak range we found
            peak_position, peak_width = self.fit_peak(signal_x_crop, signal_y_crop, peak)
            # If we are more than two sigmas away from the middle of the range,
            # there's clearly a problem.
            if np.abs(peak_position - (peak[1]+peak[0])/2.0)  > np.abs(peak[1]-peak[0]):
                logging.error("Found peak position outside of given range [x=%s], switching to full detector" % peak_position)
                peak_position = (peak[1]+peak[0])/2.0
                peak_width = (peak[1]-peak[0])/2.0
                raise RuntimeError("Bad peak position")
        except:
            # If we can't find a peak, try fitting over the full detector.
            # If we do find a peak, then update the ranges rather than using
            # what we currently have (which is probably given by the ROI).
            logging.warning("Run %s [%s]: Could not fit a peak in the supplied peak range" % (self.run_number, self.cross_section))
            logging.debug(sys.exc_value)
            try:
                peak_position, peak_width = self.fit_peak(signal_x, signal_y, self.found_peak)
                peak = [math.floor(peak_position-peak_width), math.floor(peak_position+peak_width)]
                #low_res = [5, self.n_x_pixel-5]
                low_res = self.found_low_res
                self.use_roi_actual = False
                logging.warning("Run %s [%s]: Peak not in supplied range! Found peak: %s low: %s" % (self.run_number, self.cross_section, peak, low_res))
                logging.warning("Run %s [%s]: Peak position: %s  Peak width: %s" % (self.run_number, self.cross_section, peak_position, peak_width))
            except:
                logging.debug(sys.exc_value)
                logging.error("Run %s [%s]: Could not use Gaussian fit to determine peak position over whole detector" % (self.run_number, self.cross_section))

        # Update the specular peak range if needed
        if self.update_peak_range:
            peak[0] = math.floor(peak_position-peak_width)
            peak[1] = math.ceil(peak_position+peak_width)
            self.use_roi_actual = False

        # Store the information we found
        self.peak_position = peak_position
        self.peak_range = [int(peak[0]), int(peak[1])]
        self.low_res_range = [int(low_res[0]), int(low_res[1])]

        if not self.use_roi_bck or bck_range is None:
            if self.use_tight_bck:
                self.background = [self.peak_range[0]-self.bck_offset, self.peak_range[1]+self.bck_offset]
            else:
                self.background = [4, self.peak_range[0]-30]
        else:
            self.background = [int(bck_range[0]), int(bck_range[1])]

        # Determine whether we have a direct beam 
        self.is_direct_beam = self.check_direct_beam(ws, peak_position)

        # Convenient data type
        self.data_type = 0 if self.is_direct_beam else 1

        # Write to logs
        self.log()

