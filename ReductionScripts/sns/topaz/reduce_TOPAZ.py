import sys
sys.path.append('/opt/Mantid/bin')
import numpy,os,mantid
from mantid.simpleapi import *
from matplotlib import *
use("agg")
import matplotlib.pyplot as plt

class Configuration(object):
    def __init__(self,filename):
        f=open(filename,'r')
        lines=f.readlines()
        f.close()
        self.parameters=dict()
        self.commands=[]
        for l in lines:
            if l.strip()[0]=="#":
                continue
            result=l.strip().split("=")
            if len(result)==2:
                self.process_parameter(result[0],result[1])
            elif len(result)==1:
                self.process_command(result[0])
            else:
                if len(l.strip())>0:
                    mantid.logger.warning("The line '"+l.strip()+"' was not processed")
    
    def process_parameter(self,parameterName,parameterValue):
        if parameterName in ["UBMatrixFile","VanadiumSolidAngleFile","VanadiumFluxFile","BackgroundFile"] and len(parameterValue)>0:
            self.parameters[parameterName]=parameterValue
        else:
            mantid.logger.warning("Parameter '"+parameterName+"' was not processed")
            
    def process_command(self,command):
        pieces=command.split()
        if pieces[0]!="Plot" or len(pieces) not in [2,4]:
            mantid.logger.warning("Command '"+command+"' was not processed")
            return
        if pieces[1] not in ['H','K','L']:
            mantid.logger.warning("You can only plot images perpendicular to H, K, or L.\n Command '"+command+"' was not processed")
            return
        if len(pieces)==2:
            if pieces[1]=='H':
                self.commands.append('[0,K,0];[0,0,L];[H,0,0]')
            if pieces[1]=='K':
                self.commands.append('[H,0,0];[0,0,L];[0,K,0]')
            if pieces[1]=='L':
                self.commands.append('[H,0,0];[0,K,0];[0,0,L]')
        if len(pieces)==4:
            try:
                a=float(pieces[2])
                b=float(pieces[3])
                if b>a:
                    if pieces[1]=='H':
                        self.commands.append('[0,K,0];[0,0,L];[H,0,0],'+pieces[2]+','+pieces[3]+',1')
                    if pieces[1]=='K':
                        self.commands.append('[H,0,0];[0,0,L];[0,K,0],'+pieces[2]+','+pieces[3]+',1')
                    if pieces[1]=='L':
                        self.commands.append('[H,0,0];[0,K,0];[0,0,L],'+pieces[2]+','+pieces[3]+',1')
                else:
                    mantid.logger.warning("Minimum value is not less than the maximum value.\n Command '"+command+"' was not processed")
                    return  
            except:
                mantid.logger.warning("Command '"+command+"' was not processed")
                return

def makePlots(filename,configuration,outdir):
    if not configuration.parameters.has_key("UBMatrixFile"):
        mantid.logger.warning("No UB matrix file")
        return
    if not configuration.parameters.has_key("VanadiumSolidAngleFile"):
        mantid.logger.warning("No solid angle file")
        return
    if not configuration.parameters.has_key("VanadiumFluxFile"):
        mantid.logger.warning("No flux file")
        return  
    data=Load(filename)
    sa=Load(configuration.parameters["VanadiumSolidAngleFile"])
    flux=Load(configuration.parameters["VanadiumFluxFile"])
    mommin=flux.readX(0)[0]
    mommax=flux.readX(0)[-1]
    MaskDetectors(Workspace=data,MaskedWorkspace=sa)
    data1=ConvertUnits(InputWorkspace=data,Target='Momentum')
    DeleteWorkspace(data)
    data2=CropWorkspace(InputWorkspace=data1,XMin=mommin,XMax=mommax)
    data=Rebin(InputWorkspace=data2,Params=str(mommin)+','+str(mommax-mommin)+','+str(mommax))
    LoadIsawUB(InputWorkspace=data,Filename=os.path.join(outdir,configuration.parameters["UBMatrixFile"]))
    DeleteWorkspace(data1)
    DeleteWorkspace(data2)
    md=ConvertToMD(InputWorkspace=data,QDimensions="Q3D",dEAnalysisMode="Elastic",Q3DFrames="HKL",QConversionScales="HKL")
    #SaveMD(md,os.path.join(outdir,'TOPAZ_'+str(data.getRunNumber())+'MD.nxs'))
    # Make Figures
    fig = plt.gcf()
    numfig=len(configuration.commands)
    fig.set_size_inches(6.0,6.0*numfig)
    for i in range(numfig):
        plt.subplot(numfig,1,i+1)      
        com=configuration.commands[i]
        titles=com.split(";")
        plt.xlabel(titles[0])
        dimIDX=md.getDimensionIndexByName(titles[0])
        dimX=md.getDimension(dimIDX)
        stringX=titles[0]+','+str(dimX.getMinimum())+','+str(dimX.getMaximum())+',300'
        xvals=numpy.arange(dimX.getMinimum(),dimX.getMaximum(),(dimX.getMaximum()-dimX.getMinimum())/300.)
        plt.ylabel(titles[1])
        dimIDY=md.getDimensionIndexByName(titles[1])
        dimY=md.getDimension(dimIDY)
        stringY=titles[1]+','+str(dimY.getMinimum())+','+str(dimY.getMaximum())+',300'
        yvals=numpy.arange(dimY.getMinimum(),dimY.getMaximum(),(dimY.getMaximum()-dimY.getMinimum())/300.)
        if len(titles[2])==7: 
            plt.title("Integrated "+titles[2])
            stringZ=""
        else:
            titleparts=titles[2].split('],')
            vals=titleparts[1].split(',')
            plt.title(titleparts[0]+'] from '+vals[0]+' to '+vals[1]) 
            stringZ=titleparts[0]+'],'+vals[0]+','+vals[1]+',1'
            
        a,b=MDNormSCD(InputWorkspace=md,FluxWorkspace=flux,SolidAngleWorkspace=sa,
            AlignedDim0=stringX,
            AlignedDim1=stringY,
            AlignedDim2=stringZ)
        norm=a/b
        imagevals=numpy.log(norm.getSignalArray())
        normmasked=numpy.ma.masked_where(numpy.logical_not(numpy.isfinite(imagevals)),imagevals)   
        X,Y=numpy.meshgrid(xvals,yvals)   
        plt.pcolormesh(X,Y,normmasked,shading='gouraud')
        DeleteWorkspace(a)
        DeleteWorkspace(b)
         
    #plt.show()
    processed_filename=os.path.join(outdir,'TOPAZ_'+str(data.getRunNumber())+'.png')
    plt.savefig(processed_filename, bbox_inches='tight')
    plt.close()
    DeleteWorkspace(md)
    DeleteWorkspace(flux)
    DeleteWorkspace(sa)
            
if __name__ == "__main__":
    numpy.seterr("ignore")#ignore division by 0 warning in plots

    #check number of arguments
    if (len(sys.argv) != 3): 
        mantid.logger.error("autoreduction code requires a filename and an output directory")
        sys.exit()
    if not(os.path.isfile(sys.argv[1])):
        mantid.logger.error("data file "+sys.argv[1]+ " not found")
        sys.exit()    
    else:
        filename = sys.argv[1]
        outdir = sys.argv[2]
    if not(os.path.isfile(os.path.join(outdir,"autoreduce_configuration.txt"))):
        mantid.logger.warning("no configuration file")
        sys.exit()  
    configuration=Configuration(os.path.join(outdir,"autoreduce_configuration.txt")) 
    makePlots(filename,configuration,outdir)
    
