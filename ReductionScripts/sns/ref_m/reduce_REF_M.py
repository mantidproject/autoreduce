#!/usr/bin/env python
import logging
import sys, os

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
from mr_reduction import mr_translate
from mr_reduction import oncat_comm as oncat

if __name__=="__main__":
    """
    Options:
        Use SANGLE:       True
        Use Const-Q:      False
        Fit peak in roi:  False
        Use bck ROI:      True
        Force peak:       True [174, 192]
        Force background: True [70, 110]
        Use side bck:     False
        Bck width:        10
        Skip conversion   False
        Produce 2D plots  True

    Not used yet:
        Const-Q cutoff:   None
    """

    event_file_path=sys.argv[1]
    event_file = os.path.split(event_file_path)[-1]
    outdir=sys.argv[2]
    # The legacy format is REF_L_xyz_event.nxs
    # The new format is REF_L_xyz.nxs.h5
    run_number = event_file.split('_')[2]
    run_number = run_number.replace('.nxs.h5', '')

    # Translate event data to legacy QuickNXS-compatible files.
    if not False and event_file_path.endswith('.h5'):
        mr_translate.translate(event_file_path, events=False, histo=True, sub_dir='../data')

    red = refm.ReductionProcess(data_run=event_file_path,
                                output_dir=outdir,
                                use_sangle=True,
                                const_q_binning=False,
                                const_q_cutoff=None,
                                update_peak_range=False,
                                use_roi=True,
                                use_roi_bck=True,
                                force_peak_roi=True, peak_roi=[174, 192],
                                force_bck_roi=True, bck_roi=[70, 110],
                                use_tight_bck=False, bck_offset=10)
    red.plot_2d = True
    red.reduce()
