from qtiGenie import *
iliad_setup('let')

# program to crunch down event mode from LET and produce output SPE files. Program can automatically find all incident energies in rep rate mode and write out spe files in the # form of LET'run no: +ei'.spe

#############################################
# this is the user input section
wb=11869   # enter whitebeam run number here (cycle 2013/3)
run_no=[14133] # event mode run numbers here or use next line for a continous sequence of runs i.e range(first run, last run +1)
#run_no=range(14110,14111) 
ei = [10.2,4.0,2.13,1.31]  #ei=[5.8,15]           # incident energies you want analysed, or leave as ei=[]  if you want all incident energies analysed
#ei = [4]  #ei=[5.8,15]           # incident energies you want analysed, or leave as ei=[]  if you want all incident energies analysed
#ei = [30.6,10.2,5.01,2.97]  #ei=[5.8,15]           # incident energies you want analysed, or leave as ei=[]  if you want all incident energies analysed
ebin=[-0.8,0.002,0.9]    #binning of the energy for the spe file. The numbers are as a fraction of ei [from ,step, to ]
mapping='LET_rings_133'  # rings mapping file for powders
file = '/home/let/Desktop/LET_maps/hard_133.msk'    # standard hard mask file  for LET
#file = '/home/let/Desktop/LET_maps/magnet_9T_pm45_hard.msk'  #mask for pm 45 9T magnet orientation
#file = '/home/let/Desktop/LET_maps/9Tmagnet_0to90_hard.msk'  #mask for pm 45 9T magnet orientation
#file = '/home/let/Desktop/LET_maps/hard_14Tmagnet.msk'  #14T mask
#file = '/home/let/Desktop/LET_maps/magnet7T_hard.msk'    #7T mask
############################################


##########################

LoadRaw(Filename=str(wb),OutputWorkspace="wb_wksp") # load whitebeam

######################################################################


for run in run_no:     #loop around runs
	fname='LET0000'+str(run)+'.nxs'
	print ' processing file ', fname
	#LoadEventNexus(Filename=fname,OutputWorkspace='w1',SingleBankPixelsOnly='0',LoadMonitors='1',MonitorsAsEvents='0',FilterByTimeStart='34000',FilterByTimeStop='46000')
	LoadEventNexus(Filename=fname,OutputWorkspace='w1',SingleBankPixelsOnly='0',LoadMonitors='1',MonitorsAsEvents='0')
	#LoadRaw(Filename=fname,OutputWorkspace='w1')
	Rebin(InputWorkspace='w1_monitors',OutputWorkspace='mon',Params=[1000,100,90000])
	ExtractSingleSpectrum(InputWorkspace='mon',OutputWorkspace='mon',WorkspaceIndex='5')  #extract monitor 6
	ConvertToMatrixWorkspace(InputWorkspace='mon',OutputWorkspace='mon')
	ConvertUnits(InputWorkspace='mon',OutputWorkspace='mon',Target='Energy')
	NormaliseByCurrent(InputWorkspace='mon',OutputWorkspace='mon')     #monitor 6 converted to energy and normalised
	
	##################################300
	# this section finds all the transmitted incident energies
	if len(ei) == 0:
		for x in range(0,15):
			Max(InputWorkspace='mon',OutputWorkspace='maxval')
			mv=mtd['maxval']
			if mv.dataY(0)[0] >= 250:
				min=mv.dataX(0)[0] -0.02
				max=mv.dataX(0)[1] +0.02
				RemoveBins(InputWorkspace='mon',OutputWorkspace='mon',XMin=min,XMax=max)
				ei.append(mv.dataX(0)[0])
	ei.sort()     #sorts energies into order
	print ei
	if run == run_no[0]:
		ei = [ '%.2f' % elem for elem in ei ] 
	print 'energies transmitted are:'
	print (ei)

	for energy in ei:
		energy=float(energy)
		print (energy)
		emin=0.2*energy   #minimum energy is with 80% energy loss
		lam=(81.81/energy)**0.5
		lam_max=(81.81/emin)**0.5
		tsam=252.82*lam*25   #time at sample
		tmon2=252.82*lam*23.5 #time to monitor 6 on LET
		tmax=tsam+(252.82*lam_max*4.1) #maximum time to measure inelastic signal to
		t_elastic=tsam+(252.82*lam*4.1)   #maximum time of elastic signal
		tbin=[int(tmon2),1.6,int(tmax)]
		Rebin(InputWorkspace='w1',OutputWorkspace='w1reb',Params=tbin,PreserveEvents='0')	
		Rebin(InputWorkspace='w1_monitors',OutputWorkspace='w1_mon',Params=tbin,PreserveEvents='0')	
		ConjoinWorkspaces(InputWorkspace1='w1reb',InputWorkspace2='w1_mon')
		
		

		energybin=[ebin[0]*energy,ebin[1]*energy,ebin[2]*energy]
		energybin = [ '%.4f' % elem for elem in energybin ]  
		ebinstring=str(energybin[0])+','+str(energybin[1])+','+str(energybin[2])
		print ebinstring
		
		out=iliad("wb_wksp","w1reb",energy,ebinstring,mapping,save_format='',fixei=False,bleed=False,norm_method='current',det_cal_file='det_LET_cycle133.dat',detector_van_range=[0.5,200],bkgd_range=[int(t_elastic),int(tmax)],hardmaskOnly=file)
#		out=iliad("wb_wksp","w1reb",energy,ebinstring,mapping,save_format='',fixei=False,bleed=False,norm_method='current',detector_van_range=[0.5,200],bkgd_range=[int(t_elastic),int(tmax)],hardmaskOnly=file)
		SaveNXSPE(out,'LET'+str(run)+'_'+str(energy)+'mev.nxspe') # direcotry where to save the spe/nxspe files


