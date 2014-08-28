from django.db import models
from reduction_viewer.models import Instrument, ReductionRun

class InstrumentVariable(models.Model):
    instrument = models.ForeignKey(Instrument)
    start_run = models.IntegerField(blank=False)
    name = models.CharField(max_length=50, blank=False)
    value = models.CharField(max_length=300, blank=False)
    type = models.CharField(max_length=50, blank=False)

    def __unicode__(self):
        return u'%s - %s=%s' % (self.instrument.name, self.name, self.value)

class RunVariable(models.Model):
    reduction_run = models.ForeignKey(ReductionRun)
    name = models.CharField(max_length=50, blank=False)
    value = models.CharField(max_length=300, blank=False)
    type = models.CharField(max_length=50, blank=False)

    def __unicode__(self):
        return u'%s - %s=%s' % (self.reduction_run, self.name, self.value)

class ScriptFile(models.Model):
    reduction_run = models.ForeignKey(ReductionRun, blank=False, related_name="scripts")
    script = models.BinaryField(blank=False)
    file_name = models.CharField(max_length=50, blank=False)

    def __unicode__(self):
        return u'%s' % self.file_name
