#!/usr/bin/env python
import logging
import sys, os

# This line will cause ar to pick the right mantid to run
sys.path # /opt/mantid50/bin

class ContextFilter(logging.Filter):
    """ Simple log filter to take out non-Mantid logs from .err file """

    def filter(self, record):
        filtered_logs = ["Optimal parameters not found"]
        msg = record.getMessage()
        if record.levelname == 'WARNING':
            return 0
        for item in filtered_logs:
            if item in msg:
                return 0
        return 1

logger = logging.getLogger()
f = ContextFilter()
logger.addFilter(f)

from mr_reduction import mr_reduction as refm
from mr_reduction import oncat_comm as oncat

if __name__=="__main__":
    """
    Options:
        Use SANGLE:       False
        Use Const-Q:      False
        Fit peak in roi:  True
        Use bck ROI:      False
        Force peak:       False [152, 161]
        Force background: False [90, 130]
        Use side bck:     True
        Bck width:        10
        Produce 2D plots  True
        Q step:           -0.02

    Not used yet:
        Const-Q cutoff:   None

START_JSON
{"use_sangle":False, "use_const_q":False, "fit_peak_in_roi":True, "use_roi_bck":False,
 "force_peak":False, "peak_min":152, "peak_max":161, "force_background":False,
 "bck_min":90, "bck_max":130, "use_side_bck":True, "bck_width":10, "plot_2d":True, "q_step":-0.02}
END_JSON
    """

    event_file_path=sys.argv[1]
    event_file = os.path.split(event_file_path)[-1]
    outdir=sys.argv[2]
    # The legacy format is REF_L_xyz_event.nxs
    # The new format is REF_L_xyz.nxs.h5
    run_number = event_file.split('_')[2]
    run_number = run_number.replace('.nxs.h5', '')

    red = refm.ReductionProcess(data_run=event_file_path,
                                output_dir=outdir,
                                use_sangle=False,
                                const_q_binning=False,
                                const_q_cutoff=None,
                                update_peak_range=True,
                                use_roi=True,
                                use_roi_bck=False,
                                q_step=-0.02,
                                force_peak_roi=False, peak_roi=[152, 161],
                                force_bck_roi=False, bck_roi=[90, 130],
                                use_tight_bck=True, bck_offset=10)
    red.plot_2d = True
    red.reduce()
