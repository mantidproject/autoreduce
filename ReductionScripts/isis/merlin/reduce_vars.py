standard_vars = {
         'energy_bins':[-0.25, 0.005, 0.85],
         'incident_energy':'AUTO',
         'sum_runs':False,
         'monovan_run':None,
         'wb_run':'28093.raw',
         'sample_run':28082
}
advanced_vars={
         'motor_offset':None,
        'monovan_hi_frac':0.4,
        'hardmaskOnly':'hard_cycle_15_3.msk',
        'detector_van_range':[40, 55],
        'vanadium-mass':7.85,
        'background_range':[18000, 19000],
        'save_format':'nxspe',
        'norm_method':'current',
        'det_cal_file':'det_corr_153.dat',
        'monovan_lo_frac':-0.4,
        'monovan_mapfile':'rings_153.map',
        'bleed_maxrate':0.005,
        'data_file_ext':'.nxs',
        'check_background':False,
        'bleed':True,
        'map_file':'one2one_153.map'
}
variable_help={
         'standard_vars' : {
         'energy_bins':'Energy binning, expected in final converted to energy transfer workspace.\n\n Provide it in the form:\n propman.energy_bins = [min_energy,step,max_energy]\n if energy to process (incident_energy property) has a single value,\n or\n propman.energy_bins = [min_rel_enrgy,rel_step,max_rel_energy]\n where all values are relative to the incident energy,\n if energy(ies) to process (incident_energy(ies)) are list of energies.\n The list of energies can contain only single value.\n (e.g. prop_man.incident_energy=[100])/\n ',
        'incident_energy':'Provide incident energy or range of incident energies to be processed.\n\n Set it up to list of values (even with single value i.e. prop_man.incident_energy=[10]),\n if the energy_bins property value to be treated as relative energy ranges.\n\n Set it up to single value (e.g. prop_man.incident_energy=10) to treat energy_bins\n as absolute energy values.\n ',
        'sum_runs':'Boolean property specifies if list of files provided as input for sample_run property\n should be summed.\n ',
        'monovan_run':'Run number, workspace or symbolic presentation of such run\n containing results of monochromatic neutron beam scattering from vanadium sample\n used in absolute units normalization.\n None disables absolute units calculations.',
        'wb_run':'Run number, workspace or symbolic presentation of such run\n containing results of white beam neutron scattering from vanadium used in detectors calibration.',
        'sample_run':'Run number, workspace or symbolic presentation of such run\n containing data of scattering from a sample to convert to energy transfer.\n Also accepts a list of the such run numbers',
         },
         'advanced_vars' : {
         'motor_offset':'Initial value used to identify crystal rotation angle according to the formula:\n psi=motor_offset+wccr.timeAverageValue() where wccr is the log describing\n crystal rotation. See motor_log_name property for its description.\n ',
        'hardmaskOnly':'Sets diagnostics algorithm to use hard mask file and to disable all other diagnostics.\n\n Assigning a mask file name to this property sets up hard_mask_file property\n to the file name provided and use_hard_mask_only property to True, so that\n only hard mask file provided is used to exclude failing detectors.\n ',
        'save_format':'The format to save reduced results using internal save procedure.\n\n Can be one name or list of supported format names. Currently supported formats\n are: spe, nxspe and nxs data formats.\n See Mantid documentation for detailed description of the formats.\n If set to None, internal saving procedure is not used.\n ',
        'det_cal_file':'Provide a source of the detector calibration information.\n\n A source can be a file, present on a data search path, a workspace\n or a run number, corresponding to a file to be loaded as a\n workspace.\n ',
        'monovan_mapfile':'Mapping file for the monovanadium integrals calculation.\n\n The file used to group various monochromatic vanadium spectra together to provide\n reasonable statistics for these groups when calculating monovanadium integrals.',
        'map_file':'Mapping file for the sample run.\n\n The file used to group various spectra together to obtain appropriate instrument configuration \n and improve statistics.',
         },
}
