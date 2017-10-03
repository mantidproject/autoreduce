"""
    Translator to be used to process filtered event data and procuce nexus files readable by QuickNXS.
    This translator will be part of the post-processing once REFM moves to Epics.

    For reference, these are the states recognized by QuickNXS
    
MAPPING_12FULL=(
                 (u'++ (0V)', u'entry-off_off_Ezero'),
                 (u'-- (0V)', u'entry-on_on_Ezero'),
                 (u'+- (0V)', u'entry-off_on_Ezero'),
                 (u'-+ (0V)', u'entry-on_off_Ezero'),
                 (u'++ (+V)', u'entry-off_off_Eplus'),
                 (u'-- (+V)', u'entry-on_on_Eplus'),
                 (u'+- (+V)', u'entry-off_on_Eplus'),
                 (u'-+ (+V)', u'entry-on_off_Eplus'),
                 (u'++ (-V)', u'entry-off_off_Eminus'),
                 (u'-- (-V)', u'entry-on_on_Eminus'),
                 (u'+- (-V)', u'entry-off_on_Eminus'),
                 (u'-+ (-V)', u'entry-on_off_Eminus'),
                 )
MAPPING_12HALF=(
                 (u'+ (0V)', u'entry-off_off_Ezero'),
                 (u'- (0V)', u'entry-on_off_Ezero'),
                 (u'+ (+V)', u'entry-off_off_Eplus'),
                 (u'- (+V)', u'entry-on_off_Eplus'),
                 (u'+ (-V)', u'entry-off_off_Eminus'),
                 (u'- (-V)', u'entry-on_off_Eminus'),
                 )
MAPPING_FULLPOL=(
                 (u'++', u'entry-Off_Off'),
                 (u'--', u'entry-On_On'),
                 (u'+-', u'entry-Off_On'),
                 (u'-+', u'entry-On_Off'),
                 )
MAPPING_HALFPOL=(
                 (u'+', u'entry-Off_Off'),
                 (u'-', u'entry-On_Off'),
                 )
MAPPING_UNPOL=(
               (u'x', u'entry-Off_Off'),
               )
MAPPING_EFIELD=(
                (u'0V', u'entry-Off_Off'),
                (u'+V', u'entry-On_Off'),
                (u'-V', u'entry-Off_On'),
                )
"""
import os
from nexpy.api.nexus.tree import *
import numpy as np

def translate_entry(raw_event_file, filtered_file, entry_name):
    """
        Create a nexus entry from a filtered data set
        :param str raw_event_file: name of the original event nexus file
        :param str filtered_file: Mantid processed event file (filtered)
        :param str entry_name: name of the entry to be created
    """
    # Read in processed file
    nx_processed = NXFile(filtered_file, 'r')
    tree_processed = nx_processed.readfile()

    # Read in raw file
    nx_raw = NXFile(raw_event_file, 'r')
    tree_raw = nx_raw.readfile()

    # Create a QuickNXS file
    nx_quick = NXentry(name=entry_name)

    start_time_value = str(tree_raw.NXentry[0].start_time[0])
    start_time = NXfield(name='start_time', dtype='char', value=[start_time_value])
    nx_quick.start_time = start_time

    end_time_value = str(tree_raw.NXentry[0].end_time[0])
    end_time = NXfield(name='end_time', dtype='char', value=[end_time_value])
    nx_quick.end_time = end_time

    nx_quick.instrument = tree_raw.NXentry[0].instrument
    nx_quick.sample = tree_raw.NXentry[0].sample
    nx_quick.SNSproblem_log_geom = tree_raw.NXentry[0].SNSproblem_log_geom

    nx_quick.proton_charge = NXfield(name='proton_charge', dtype='float64', value=[float(tree_raw.NXentry[0].proton_charge),])
    nx_quick.total_counts = NXfield(name='total_counts', dtype='uint64', value=[float(tree_raw.NXentry[0].total_counts),])
    nx_quick.duration = NXfield(name='duration', dtype='float64', value=[float(tree_raw.NXentry[0].duration),])

    nx_quick.experiment_identifier = NXfield(name='experiment_identifier', dtype='char', value=[str(tree_raw.NXentry[0].experiment_identifier)])
    nx_quick.run_number = NXfield(name='run_number', dtype='char', value=[str(tree_raw.NXentry[0].run_number)])
    nx_quick.SNSproblem_log_geom.data = NXfield(name='data', dtype='char', value=[str(tree_raw.NXentry[0].SNSproblem_log_geom.data)])

    # DAS logs
    nx_quick.DASlogs = NXgroup(name='DASlogs', nxclass='NXcollection')
    for item in tree_processed.NXentry[0].logs:
        exec("nx_quick.DASlogs.%s = tree_processed.NXentry[0].logs[item]" % item)

        if not hasattr(tree_processed.NXentry[0].logs[item], 'value'):
            continue

        if len(tree_processed.NXentry[0].logs[item].value.shape) == 0:
            if not str(tree_processed.NXentry[0].logs[item].value.dtype.kind) == "S":
                exec("value = float(nx_quick.DASlogs.%s.value)" % item)
                exec("nx_quick.DASlogs.%s.value = NXfield(name='value', dtype='float64', value=[value,])" % item)
            if hasattr(tree_processed.NXentry[0].logs[item], 'time'):
                exec("time = float(nx_quick.DASlogs.%s.time)" % item)
                exec("nx_quick.DASlogs.%s.time = NXfield(name='time', dtype='float64', value=[time,])" % item)
        else:
            if not str(tree_processed.NXentry[0].logs[item].value.dtype.kind) == "S":
                exec("value = np.asarray(nx_quick.DASlogs.%s.value)" % item)
                exec("nx_quick.DASlogs.%s.value = NXfield(name='value', dtype='float64', value=value)" % item)
            if hasattr(tree_processed.NXentry[0].logs[item], 'time'):
                exec("time = np.asarray(nx_quick.DASlogs.%s.time)" % item)
                exec("nx_quick.DASlogs.%s.time = NXfield(name='time', dtype='float64', value=time)" % item)

    # Links that QuickNXS uses
    nx_quick.instrument.analyzer.AnalyzerLift = nx_quick.DASlogs.AnalyzerLift
    nx_quick.instrument.polarizer.PolLift = nx_quick.DASlogs.PolLift
    nx_quick.instrument.bank1.DANGLE = nx_quick.DASlogs.DANGLE
    nx_quick.instrument.bank1.DANGLE0 = nx_quick.DASlogs.DANGLE0
    nx_quick.instrument.bank1.DIRPIX = nx_quick.DASlogs.DIRPIX
    nx_quick.instrument.bank1.SampleDetDis = nx_quick.DASlogs.SampleDetDis
    nx_quick.instrument.moderator.ModeratorSamDis = nx_quick.DASlogs.ModeratorSamDis
    nx_quick.instrument.aperture1.S1HWidth = nx_quick.DASlogs.S1HWidth
    nx_quick.instrument.aperture2.S2HWidth = nx_quick.DASlogs.S2HWidth
    nx_quick.instrument.aperture3.S3HWidth = nx_quick.DASlogs.S3HWidth
    nx_quick.sample.SANGLE = nx_quick.DASlogs.SANGLE

    # Some values need to be transformed
    value = float(nx_quick.instrument.aperture1.distance)
    nx_quick.instrument.aperture1.distance = NXfield(name='value', dtype='float64', value=[value,])
    value = float(nx_quick.instrument.aperture2.distance)
    nx_quick.instrument.aperture2.distance = NXfield(name='value', dtype='float64', value=[value,])
    value = float(nx_quick.instrument.aperture3.distance)
    nx_quick.instrument.aperture3.distance = NXfield(name='value', dtype='float64', value=[value,])

    # The Data
    nx_quick.bank1 = tree_raw.NXentry[0].bank1
    nx_quick.bank1_events = NXgroup(name='bank1_events', nxclass='NXevent_data')
    nx_quick.bank1_events.event_time_offset = tree_processed.NXentry[0].event_workspace.tof

    # The events are assigned to pixels through an array of indices in Mantid nexus files.
    # All the events for a given pixel are stored in a block in the tof array above.
    # The array indices in that block go from indices[i] to indices[i+1], where i is the ith pixel.
    indices = np.asarray(tree_processed.NXentry[0].event_workspace.indices)
    event_ids = []
    for i in range(len(indices)-1):
        n_events = int(indices[i+1]-indices[i])
        event_ids.extend(n_events*[i])

    # In the raw SNS nexus file, event_id is a pixel ID
    nx_quick.bank1_events.event_id =  NXfield(name='event_id', dtype='uint32', value=event_ids)
    nx_quick.total_counts = NXfield(name='total_counts', dtype='uint64', value=[len(event_ids),])

    return nx_quick

def filter_events(raw_event_file):
    """
        Filter an event nexus file
        :param str raw_event_file: name of the event data file
    """
    return {'entry-Off_Off':'filtered.nxs', 'entry-On_Off':'filtered.nxs'}

def translate(raw_event_file, identifier='quick'):
    """
        Translate an event nexus file
        :param str raw_event_file: name of the event data file to process
        :param str identifier: suffix for the output data file
    """
    # Create a filtered file
    filtered_files = filter_events(raw_event_file)

    # Assemble the entries
    tree = NXroot()
    for entry_name, filtered_file in filtered_files.items():
        entry = translate_entry(raw_event_file, filtered_file , entry_name=entry_name)
        tree.insert(entry)

    # Save output file. Should normally be: nx_quick.save('test_event.nxs')
    # Nexpy has a bug in its file writer so we bypass some of it here.
    def _rootattrs(): return

    # Create a name that QuickNXS will recognize
    if raw_event_file.endswith('_event.nxs'):
        output_file = raw_event_file.replace('_event.nxs', '_%s_event.nxs' % identifier)
    elif raw_event_file.endswith('.nxs.h5'):
        output_file = raw_event_file.replace('.nxs.h5', '_event.nxs')
    if os.path.isfile(output_file):
        os.remove(output_file)

    with NXFile(output_file, mode='w') as f:
        f._rootattrs = _rootattrs
        f.file.attrs['file_name'] = output_file
        f.writefile(tree)

if __name__ == '__main__':
    # Example data files
    # /SNS/REF_M/IPTS-17695/data/REF_M_26403_histo.nxs
    # /SNS/REF_M/IPTS-17695/data/REF_M_26403_event.nxs
    translate('REF_M_26403_event.nxs')

