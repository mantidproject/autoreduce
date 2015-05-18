from django.db import models
from django.contrib.auth.models import User
from autoreduce_webapp.utils import SeparatedValuesField
import autoreduce_webapp.icat_communication

class Instrument(models.Model):
    name = models.CharField(max_length=80)
    is_active = models.BooleanField(default=False)

    def __unicode__(self):
        return u'%s' % self.name

class Experiment(models.Model):
    reference_number = models.IntegerField()

    def __unicode__(self):
        return u'%s' % self.reference_number

    def get_ICAT_details():
        return icat_communication.get_experiment_details(reference_number)

class Status(models.Model):
    value = models.CharField(max_length=25)

    def __unicode__(self):
        return u'%s' % self.value

class ReductionRun(models.Model):
    instrument = models.ForeignKey(Instrument, related_name='reduction_runs', null=True)
    run_number = models.IntegerField(blank=False)
    run_name = models.CharField(max_length=50,blank=True)
    run_version = models.IntegerField(blank=False)
    experiment = models.ForeignKey(Experiment,blank=False, related_name='reduction_runs')
    created = models.DateTimeField(auto_now_add=True,blank=False)
    started_by = models.IntegerField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True,blank=False)
    status = models.ForeignKey(Status, blank=False, related_name='+', default=1)
    started = models.DateTimeField(null=True, blank=True)
    finished = models.DateTimeField(null=True, blank=True)
    message = models.CharField(max_length=255,blank=True)
    graph = SeparatedValuesField(null=True, blank=True)

    def __unicode__(self):
        if self.run_name:
            return u'%s-%s' % (self.run_number, self.run_name)
        else:
            return u'%s' % self.run_number

    def title(self):
        """
        Return a interface-friendly name that identifies this run using either run name or run version
        """
        if self.run_version > 0:
            if self.run_name:
                title = '%s - %s' % (self.run_number, self.run_name)
            else:
                title = '%s - %s' % (self.run_number, self.run_version)
        else:
            title = '%s' % self.run_number
        return title

class DataLocation(models.Model):
    file_path = models.CharField(max_length=255)
    reduction_run = models.ForeignKey(ReductionRun, blank=False, related_name='data_location')
    
    def __unicode__(self):
        return u'%s' % self.file_path

class ReductionLocation(models.Model):
    file_path = models.CharField(max_length=255)
    reduction_run = models.ForeignKey(ReductionRun, blank=False, related_name='reduction_location')
    
    def __unicode__(self):
        return u'%s' % self.file_path

class Setting(models.Model):
    name = models.CharField(max_length=50, blank=False)
    value = models.CharField(max_length=50)

    def __unicode__(self):
        return u'%s=%s' % (self.name, self.value)

class Notification(models.Model):
    SEVERITY_CHOICES = (
        ('i', 'info'),
        ('w', 'warning'),
        ('e', 'error')
    );

    message = models.CharField(max_length=255, blank=False)
    is_active = models.BooleanField(default=True)
    severity = models.CharField(max_length=1,choices=SEVERITY_CHOICES,default='i')
    is_staff_only = models.BooleanField(default=False)

    def __unicode__(self):
        return u'%s' % self.message

    def severity_verbose(self):
        """
        Return the severity as its textual value
        """
        return dict(Notification.SEVERITY_CHOICES)[self.severity]