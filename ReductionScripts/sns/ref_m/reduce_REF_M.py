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
        Fit peak in roi:  False
        Use bck ROI:      True
        Force peak:       True [140, 173]
        Force background: True [85, 130]
        Use side bck:     False
        Bck width:        10
        Produce 2D plots  True

    Not used yet:
        Const-Q cutoff:   None

START_JSON
{"use_sangle":False, "use_const_q":False, "fit_peak_in_roi":False, "use_roi_bck":True,
 "force_peak":True, "peak_min":140, "peak_max":173, "force_background":True,
 "bck_min":85, "bck_max":130, "use_side_bck":False, "bck_width":10, "plot_2d":True
}
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
                                update_peak_range=False,
                                use_roi=True,
                                use_roi_bck=True,
                                force_peak_roi=True, peak_roi=[140, 173],
                                force_bck_roi=True, bck_roi=[85, 130],
                                use_tight_bck=False, bck_offset=10)
    red.plot_2d = True
    red.reduce()
