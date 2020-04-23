#!/usr/bin/env python
from __future__ import (absolute_import, division, print_function, unicode_literals)

import sys,os
#sys.path.insert(0,"/opt/mantid50/bin")
#sys.path.insert(1,"/opt/mantid50/lib")

from mantid.simpleapi import *
from mantid import logger
from io import BytesIO
import base64
import numpy as np
np.seterr("ignore")

from matplotlib import *
use("agg")
import matplotlib.pyplot as plt

try:
    from postprocessing.publish_plot import publish_plot
except ImportError:
    from finddata.publish_plot import publish_plot

class processInputs(object):
    def __init__(self):
        #templated stuff
        self.ub_matrix_file='SNS/CORELLI/IPTS-21454/shared/250mK/optub_250mK.mat' #'/SNS/CORELLI/IPTS-12310/shared/Sr214-Tb1000-2nd-20150512/UB-H0L-may12.mat'
        self.vanadium_SA_file='/SNS/CORELLI/IPTS-21454/shared/scripts/SA_CC_tot.nxs' #'/SNS/CORELLI/shared/Vanadium/SolidAngle20150411.nxs'
        self.vanadium_flux_file='/SNS/CORELLI/IPTS-21454/shared/scripts/Spec_OC_tot.nxs' #'/SNS/CORELLI/shared/Vanadium/Spectrum20150411.nxs'
        self.mask=[] #[{'Tube':'1,2,3,4','Bank':'','Pixel':''}]
        self.plot_requests=[{'Minimum': '-0.1', 'PerpendicularTo': '[0,K,0]', 'Maximum': '0.1'}] #[{'PerpendicularTo':"[0,K,0]",'Minimum':'-0.05','Maximum':'0.05'},{'PerpendicularTo':"[0,K,0]",'Minimum':'10.95','Maximum':'11.05'},{'PerpendicularTo':"[0,K,0]",'Minimum':'0.95','Maximum':'1.05'}]
        self.useCC='True' #"True"
        #other
        self.can_do_HKL=False
        self.saveMD=False
        self.can_do_norm=False
        self.good_mask=False
        self.plots=[]

    def validate(self):
        # validate normalization
        if os.path.isfile(self.vanadium_SA_file) and os.path.isfile(self.vanadium_flux_file):
            try:
                Load(self.vanadium_SA_file,OutputWorkspace='autoreduction_sa')
                Load(self.vanadium_flux_file,OutputWorkspace='autoreduction_flux')
                self.can_do_norm=True
            except:
                logger.warning("Could not load normalization vanadium")
                self.can_do_norm=False
        # if ub_matrix_file not given us newest *.mat in IPTS shared directory
        if self.ub_matrix_file == '':
            mat_list=[]
            for root, dirs, files in os.walk(os.path.abspath(os.path.join(sys.argv[2],".."))): # Look in IPTS shared
                for f in files:
                    if f.endswith(".mat"):
                        mat_list.append(os.path.join(root, f))
            if len(mat_list)==0:
                self.ub_matrix_file = ''
            else:
                self.ub_matrix_file = max(mat_list,key=os.path.getctime)
        # validate UB
        if os.path.isfile(self.ub_matrix_file):
            try:
                autoreduction_ub=CreateSingleValuedWorkspace(0.)
                LoadIsawUB(InputWorkspace=autoreduction_ub,Filename=self.ub_matrix_file)
                if autoreduction_ub.sample().hasOrientedLattice():
                    self.can_do_HKL=True
                else:
                    self.can_do_HKL=False
                    logger.warning("Could not load UB")
            except:
                self.can_do_HKL=False
                logger.warning("Could not load UB")
        # validate mask
        self.good_mask=False
        lenMask=len(self.mask)
        if lenMask>0:
            self.good_mask=True
            for i in range(lenMask):
                dicti=self.mask[i]
                if not isinstance(dicti,dict) or set(dicti.keys()).issubset(set(['Bank','Tube','Pixel'])):
                    self.good_mask=False
        if not self.good_mask:
            logger.warning("BTP mask is missing or invalid. It will be ignored")
        # validate plotting options
        for pl in self.plot_requests:
            if not isinstance(pl,dict):
                logger.warning("this is not a dict: "+str(pl))
                continue
            if set(pl.keys())!=set(['PerpendicularTo','Minimum','Maximum']):
                logger.warning("There are not enough or some invalid keys: "+str(pl.keys()))
                continue
            if pl['PerpendicularTo'] not in ['Q_sample_x','Q_sample_y','Q_sample_z','[H,0,0]','[0,K,0]','[0,0,L]']:
                logger.warning("Could not find this direction: "+str(pl['PerpendicularTo']))
                continue
            if not self.can_do_HKL and pl['PerpendicularTo'] in ['[H,0,0]','[0,K,0]','[0,0,L]']:
                logger.warning("Will not be able to convert to HKL")
                continue
            if self.can_do_HKL and pl['PerpendicularTo'] not in ['[H,0,0]','[0,K,0]','[0,0,L]']:
                logger.warning("Data will be in HKL - picture not created")
                continue
            self.plots.append(pl)

def makeInstrumentView(ws):
    wi=Integration(ws)
    plt.axis('off')
    rowA=np.transpose(wi.extractY()[0:118784].reshape([464,256]))
    rowB=np.transpose(wi.extractY()[118784:253952].reshape([528,256]))
    rowC=np.transpose(wi.extractY()[253952:372736].reshape([464,256]))
    rowA=np.concatenate((np.zeros([256,32]),rowA,np.zeros([256,32])),axis=1)
    rowC=np.concatenate((np.zeros([256,32]),rowC,np.zeros([256,32])),axis=1)
    inst=np.concatenate((rowA,rowB,rowC),axis=0)
    x=np.arange(0,528)
    y=np.arange(0,768)
    X,Y=np.meshgrid(x,y)
    instM=np.ma.masked_where(inst==0,inst)
    plt.pcolormesh(X,Y,np.log(instM),shading='gouraud',rasterized=True)
    
def makePlot(mdws,plotConfig,normalize):
    # create dimension strings
    d2=mdws.getDimensionIndexByName(plotConfig['PerpendicularTo'])
    d0=(d2+1)%3
    d1=(d2+2)%3
    dim0=mdws.getDimension(d0)
    AlignedDim0=dim0.getName()+','+str(dim0.getMinimum())+','+str(dim0.getMaximum())+',500'
    dim1=mdws.getDimension(d1)
    AlignedDim1=dim1.getName()+','+str(dim1.getMinimum())+','+str(dim1.getMaximum())+',500'
    dim2=mdws.getDimension(d2)
    if plotConfig['Minimum']=='':
        d2min=dim2.getMinimum()
    else:
        d2min=float(plotConfig['Minimum'])
    if plotConfig['Maximum']=='':
        d2max=dim2.getMaximum()
    else:
        d2max=float(plotConfig['Maximum'])
    if d2min>d2max:
        d2min=dim2.getMinimum()
        d2max=dim2.getMaximum()
    AlignedDim2=dim2.getName()+','+str(d2min)+','+str(d2max)+',1'
    if normalize:
        a,b=MDNormSCD(InputWorkspace=mdws,
                      FluxWorkspace='autoreduction_flux',
                      SolidAngleWorkspace='autoreduction_sa',
                      AlignedDim0=AlignedDim0,
                      AlignedDim1=AlignedDim1,
                      AlignedDim2=AlignedDim2)
        wsToPlot=a/b
    else:
        wsToPlot=BinMD(InputWorkspace=mdws,
                     AlignedDim0=AlignedDim0,
                     AlignedDim1=AlignedDim1,
                     AlignedDim2=AlignedDim2)
    xvals=numpy.arange(dim0.getMinimum(),dim0.getMaximum(),(dim0.getMaximum()-dim0.getMinimum())/500.)
    yvals=numpy.arange(dim1.getMinimum(),dim1.getMaximum(),(dim1.getMaximum()-dim1.getMinimum())/500.)
    arrayToPlot=np.log(wsToPlot.getSignalArray()[:,:,0]) #this is for next mantid release, or nightly
    #arrayToPlot=np.log(wsToPlot.getSignalArray())
    arrayToPlot[np.where(np.logical_not(np.isfinite(arrayToPlot)))]=0.
    arrayToPlot_where = np.argwhere(arrayToPlot)
    xstart=0
    ystart=0
    ystop=0
    xstop=0
    if arrayToPlot_where.size>0:
        (xstart, ystart), (xstop,ystop) = arrayToPlot_where.min(0), arrayToPlot_where.max(0)+1
    if ystart==ystop or xstart==xstop:
        X,Y=np.meshgrid(xvals,yvals)
        plt.pcolormesh(X,Y,arrayToPlot,shading='gouraud')
    else:
        arrayToPlot_trim = arrayToPlot[xstart:xstop, ystart:ystop]
        Y,X=np.meshgrid(yvals[ystart:ystop],xvals[xstart:xstop])
        normmasked=np.ma.masked_where(arrayToPlot_trim==0,arrayToPlot_trim)
        plt.pcolormesh(X,Y,normmasked,shading='gouraud')
    plt.xlabel(dim0.getName())
    plt.ylabel(dim1.getName())
    plt.title(dim2.getName()+' integrated from '+"{0:.3f}".format(d2min)+' to '+"{0:.3f}".format(d2max)) 

if __name__ == "__main__":
    # check number of arguments
    if (len(sys.argv) != 3): 
        logger.error("autoreduction code requires a filename and an output directory")
        sys.exit()
    if not(os.path.isfile(sys.argv[1])):
        logger.error("data file "+sys.argv[1]+ " not found")
        sys.exit()    
    else:
        filename = sys.argv[1]
        outdir = sys.argv[2]
    nexus_file=sys.argv[1]
    output_directory=sys.argv[2]
    output_file=os.path.split(nexus_file)[-1].replace('.nxs.h5','')

    # load file
    raw=Load(nexus_file)
    runNumber = raw.getRunNumber()
    
    # Do the cross-correlation and save the file
    try:
        cc=CorelliCrossCorrelate(raw,56000)
    except RuntimeError as e:
        logger.warning("Cross Correlation failed because: " + str(e))
        CCsucceded=False
    else:
        SaveNexus(cc, Filename=output_directory+output_file+"_elastic.nxs")
        CCsucceded=True

    # validate inputs
    config=processInputs()
    config.validate()

    # Masking - use vanadium, then add extra masks
    if config.can_do_norm:
        MaskDetectors(Workspace=raw,MaskedWorkspace='autoreduction_sa')
    if config.good_mask:
        for d in config.mask:
            if d.values()!=['', '', '']:
                MaskBTP(raw,**d)
    if CCsucceded:
        MaskDetectors(Workspace=cc,MaskedWorkspace=raw)
    
    # convert to momentum add goniometer and UB
    raw=ConvertUnits(raw,Target="Momentum",EMode="Elastic")
    if CCsucceded:
        cc=ConvertUnits(cc,Target="Momentum",EMode="Elastic")
    kmin=2.5
    kmax=10.
    if config.can_do_norm:
        kmin=mtd['autoreduction_flux'].readX(0)[0]
        kmax=mtd['autoreduction_flux'].readX(0)[-1]
    raw=CropWorkspace(raw,XMin=kmin,XMax=kmax)
    if CCsucceded:
        cc=CropWorkspace(cc,XMin=kmin,XMax=kmax)
    SetGoniometer(raw,Axis0="BL9:Mot:Sample:Axis1,0,1,0,1")
    if CCsucceded:
        SetGoniometer(cc,Axis0="BL9:Mot:Sample:Axis1,0,1,0,1")
    if config.can_do_HKL:
        CopySample(InputWorkspace='autoreduction_ub',OutputWorkspace=raw,CopyName=0,CopyMaterial=0,CopyEnvironment=0,CopyShape=0,CopyLattice=1)
        if CCsucceded:
            CopySample(InputWorkspace='autoreduction_ub',OutputWorkspace=cc,CopyName=0,CopyMaterial=0,CopyEnvironment=0,CopyShape=0,CopyLattice=1)

    # convert to MD
    if config.can_do_norm:
        LorentzCorrection="0"
    else:
        LorentzCorrection="1"
    if config.can_do_HKL:
        Q3DFrames="HKL"
        QConversionScales="HKL"
    else:
        Q3DFrames="Q_sample"
        QConversionScales="Q in A^-1"
    minn,maxx = ConvertToMDMinMaxGlobal(InputWorkspace=raw,QDimensions='Q3D',dEAnalysisMode='Elastic')
    mdraw = ConvertToMD(raw,QDimensions="Q3D",dEAnalysisMode="Elastic",Q3DFrames=Q3DFrames,
                        LorentzCorrection=LorentzCorrection,MinValues=minn,MaxValues=maxx)
    if CCsucceded:
        mdcc  = ConvertToMD(cc,QDimensions="Q3D",dEAnalysisMode="Elastic",Q3DFrames=Q3DFrames,
                            LorentzCorrection=LorentzCorrection,MinValues=minn,MaxValues=maxx)   

    # Save normalized MDs, if possible
    if config.can_do_norm and config.saveMD:
        if config.can_do_HKL:
            AlignedDim0='[H,0,0],'+str(minn[0])+','+str(maxx[0])+',300'
            AlignedDim1='[0,K,0],'+str(minn[1])+','+str(maxx[1])+',300'
            AlignedDim2='[0,0,L],'+str(minn[2])+','+str(maxx[2])+',300'
        else:
            AlignedDim0='Q_sample_x,'+str(minn[0])+','+str(maxx[0])+',300'
            AlignedDim1='Q_sample_y,'+str(minn[1])+','+str(maxx[1])+',300'
            AlignedDim2='Q_sample_z,'+str(minn[2])+','+str(maxx[2])+',300'
        mdrawgrid,mdnorm=MDNormSCD(InputWorkspace=mdraw,
                                   AlignedDim0=AlignedDim0,AlignedDim1=AlignedDim1,AlignedDim2=AlignedDim2,
                                   FluxWorkspace='autoreduction_flux',SolidAngleWorkspace='autoreduction_sa')
        if CCsucceded:
            mdccgrid=BinMD(InputWorkspace=mdcc,AlignedDim0=AlignedDim0,AlignedDim1=AlignedDim1,AlignedDim2=AlignedDim2)
        SaveMD(mdrawgrid,Filename=os.path.join(output_directory,output_file+"_data_MD.nxs"))
        if CCsucceded:
            SaveMD(mdccgrid,Filename=os.path.join(output_directory,output_file+"_datacc_MD.nxs"))
            SaveMD(mdcc,Filename=os.path.join(output_directory,output_file+"_datacc_MDE.nxs"))
        SaveMD(mdnorm,Filename=os.path.join(output_directory,output_file+"_norm_MD.nxs"))
        SaveMD(mdraw,Filename=os.path.join(output_directory,output_file+"_data_MDE.nxs"))
        
    # do some plots
    fig = plt.gcf()
    numfig=len(config.plots)
    fig.set_size_inches(5.0,5.0*(numfig+1))
    for i in range(numfig):
        plt.subplot(numfig+1,1,i+2)
        if config.useCC=="True" and CCsucceded:
            makePlot(mdcc,config.plots[i],config.can_do_norm)
        else:
            makePlot(mdraw,config.plots[i],config.can_do_norm)
    plt.subplot(numfig+1,1,1)
    raw=Rebin(raw,str(kmin)+','+str(kmax-kmin)+','+str(kmax))
    makeInstrumentView(raw)

    figfile = BytesIO()
    plt.savefig(figfile, bbox_inches='tight')
    plt.close()

    figfile.seek(0)
    figdata_png = base64.b64encode(figfile.getvalue())
    try:
        figdata_png = figdata_png.decode()
    except:
        pass
    div = '<div><img alt="{}" src="data:image/png;base64,{}" /></div>'.format(output_file, figdata_png)
    with open("div.txt", "w") as f:
        f.write(div)
    request = publish_plot('CORELLI', runNumber, files={'file': div})
    print(request)
