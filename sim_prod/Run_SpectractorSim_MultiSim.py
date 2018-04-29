#-------------------------------------------------------------------------------------------
# coding: utf-8

# # Spectractor Simulation
# 
# Goal is to process a series of images in order to produce spectra
# 
# - author Sylvie Dagoret-Campagne
# - date : April 05th 2018
# - update : April 29th 2018
# 

# # SpectractorSim Launcher

import sys
import os
import glob
import pandas as pd
import numpy as np

from optparse import OptionParser

PATH_SPECTRACTOR='../../Spectractor'
PATH_SPECTRACTORSIM='..'
PATH_GMAOMERRA='../merra2'



sys.path.append(PATH_SPECTRACTOR)
sys.path.append(PATH_SPECTRACTORSIM)
sys.path.append(PATH_GMAOMERRA)


from spectractor import *
from spectractorsim import *
import libMerra2 as m2

run_spectractorsim_path = os.path.dirname(__file__)

#-------------------------------------------------------------------------------------
## Configuration
#----------------------------------------------------------------------------------

### Spectra Input Directory

home=os.getenv('HOME')

#path_data=os.path.join(home,'DATA/CTIODataJune2017_reduced_RG715_v2_prod1')
path_data=os.path.join('/sps/lsst/data/AtmosphericCalibration','CTIODataJune2017_reduced_RG715_v2_prod1')


All_Subdirs=['data_28may17','data_29may17','data_30may17','data_31may17','data_01jun17','data_02jun17',
            'data_03jun17','data_04jun17','data_06jun17','data_08jun17','data_09jun17','data_10jun17',
            'data_12jun17','data_13jun17']

All_Subdirs=np.array(All_Subdirs)
 
Flag_Photometric_Nights=[False,False,True,False,False,False,False,False,False,True,False,True,True,False]




# ## Simulation mode
#------------------------

# Defines three typical atmospheric conditions:
# - *clearsky* : no aerosols, no PWV, ozone =300 DU
# - *standard* : aer=0.05, pwv=4mm, ozone =300 DU 
# - *merra2*   : parameters taken from merra2


Sim_Modes=['clearsky','standard','merra2' ]




# ## Logbook
#------------------    
# For the moment, the logbook is in the local directory

file_logbook_csv=os.path.join(PATH_SPECTRACTOR,'ctiofulllogbook_jun2017_v4.csv')
df_ctio_lbk=pd.read_csv(file_logbook_csv,sep=';')
#df_ctio_lbk.columns
df_ctio_lbk=df_ctio_lbk.reindex(columns=['date','P','T','RH','airmass','seeing','exposure','object','filter','disperser','focus','W','subdir','file']).set_index('date').sort_index()
df_ctio_lbk.head()





# ## MERRA2
#--------------------------------------------------------------


file_merra2=os.path.join(PATH_GMAOMERRA,'MERRA2_2017_M2I1NXASM_M2T1NXAER_M2T1NXRAD_ctio_AllYear.csv')
df_merra2=pd.read_csv(file_merra2,index_col=0)
df_merra2.index.name='time'
# convert the string into timestamp
#-------------------------------------
all_datetime_merra2=pd.to_datetime(df_merra2.index.get_values())
df_merra2.head()


# ## SpectractorSim config

# ### Setting the parameters of SpectractorSim

parameters.VERBOSE = False
parameters.DEBUG = False


def get_image_filename(filename):
    """
    Retretrieve the image name from the spectrum filename
    """
    base_filename=os.path.basename(filename)
    dir_filename=os.path.dirname(filename)
    rootname,ext=base_filename.split('.')
    splitrootname=rootname.split('_')
    fn=splitrootname[0]+'_'+splitrootname[1]+'_'+splitrootname[2]+'.'+ext
    tag=splitrootname[1]+'_'+splitrootname[2]
    return fn,tag

#---------------------------------------------------------------------------------------------
# # Simulation

# - loop on the spectra filename
# - extract the image filename
# - identify the row in the logbook corresponding to the image filename
# - extract the image time and pressure
#-----------------------------------------------------------------------------------------------
if __name__ == "__main__":
    
    

    parser = OptionParser()
    parser.add_option("-d", "--debug", dest="debug",action="store_true",
                      help="Enter debug mode (more verbose and plots).",default=False)
    parser.add_option("-v", "--verbose", dest="verbose",action="store_true",
                      help="Enter verbose (print more stuff).",default=False)
    parser.add_option("-o", "--output_directory", dest="output_directory", default="test/",
                      help="Write results in given output directory (default: ./tests/).")
    parser.add_option("-i", "--input_directory", dest="input_directory", default="data_30may17",
                      help="Define from where the reconstructued spectra will be taken (default: data_30may17).")
    
    (opts, args) = parser.parse_args()

    
    count =np.sum(All_Subdirs==opts.input_directory)
    if count==1:
        idx_sel_subdir=np.where(All_Subdirs==opts.input_directory)[0][0]
    else:
        print 'bad input directory selection : opts.input_directory = ',opts.input_directory    
        sys.exit()
    
    #### 1) Select one directory to produce the data
    #---------------------------------------------------------
    #idx_sel_subdir=2
    path_spectra=os.path.join(path_data,All_Subdirs[idx_sel_subdir])
    search_string=os.path.join(path_spectra,'*.fits')
    all_spectrafiles=glob.glob(search_string)
    all_spectrafiles=sorted(all_spectrafiles)

   
    #### 2)  Output directory
    #----------------------

    # defines the different output directories corresponding to each simulation mode
    topoutputdir=os.path.join("./CTIODataJune2017_reduced_RG715_v2_prod1_SimSpectra",All_Subdirs[idx_sel_subdir])
    all_outputdirs=[]
    for simmode in Sim_Modes:
        outputdir=os.path.join(topoutputdir,simmode)
        all_outputdirs.append(outputdir)
        ensure_dir(outputdir)

    #### 3) Extract the relevant data and sort by the column index
    #---------------------------------------------------------------
    all_obs=df_ctio_lbk.loc[(df_ctio_lbk["subdir"]==All_Subdirs[idx_sel_subdir])].sort_index()
    all_obs.head()
    
    
    #### 4) Loop on  simulations
    
    # loop over input files
    for idx,theinputfilename in np.ndenumerate(all_spectrafiles):   
        image_fn,tagname=get_image_filename(theinputfilename)
        dts=all_obs[all_obs.file==image_fn]  # exctract the info from the logbook
    
        #extract info from the logbook
        thetime_ctio=dts.index.get_values()[0]
        theobject_ctio=dts["object"][0]
        thepressure_ctio=dts["P"][0]
        thetemperature_ctio=dts["T"][0]
        theairmass_ctio=dts['airmass']
    
        #extract the info from MERRA2
        timestamp0=pd.to_datetime(thetime_ctio)
        ps_m2,pwv_m2,ozone_m2,aer_m2,clouds_m2,deltat1_m2,deltat2_m2=m2.GetAtmosphericParameters(timestamp0,df_merra2)
    
        #decide which weather conditions should be used
        if thepressure_ctio>700:
            thepressure_tosim=thepressure_ctio
            thetemperature_tosim=thetemperature_ctio
    
        else:
            # do not take the pressure of Merra2 which is over-estimated
            thepressure_tosim=782.5  # this value is hardcoded in SpectractorSim if thepressure_ctio is wrong, ie thepressure_ctio=-4
            thetemperature_tosim=10.0
        
        # initialisation of values to sim
        pwv_tosim=0.
        ozone_tosim=300.
        aer_tosim=0.
        clouds_tosim=clouds_m2 # on extinction is apllied, but only kept by memory
    
        # loop on pre-defined simulation  modes
        for idx2,simmode in np.ndenumerate(Sim_Modes):
            # defines output
            outputdir=all_outputdirs[idx2[0]]  # the directory where the result are to be written
        
            # defines simulation conditions
            if simmode=='clearsky':
                pwv_tosim=0.
                ozone_tosim=300.
                aer_tosim=0.
            
            elif simmode=='standard':
                pwv_tosim=4.0
                ozone_tosim=300.
                aer_tosim=0.05
          
            elif simmode=='merra2':
                pwv_tosim=pwv_m2
                ozone_tosim=300.
                aer_tosim=0.
            else:
                print 'unknown sim mode :',simmode
        
            # simulate the spectrum
            spectrum_simulation = SpectractorSim(theinputfilename,outputdir,lambdas=WL,pwv=pwv_tosim,ozone=ozone_tosim,aerosols=aer_tosim)
            
            #save simulation conditions in a logfile
            simu_log={'time': [thetime_ctio],'object':[theobject_ctio],'airmass': [theairmass_ctio],
                  'P':[thepressure_tosim],'T':[thetemperature_tosim],
                 'pwv':[pwv_tosim],'ozone':[ozone_tosim],'aer':[aer_tosim],'clouds':[clouds_tosim],'simumode':[simmode]}
            filename_log='log_simu'+'_'+tagname+'.csv'
            dts_log=pd.DataFrame(data=simu_log)
            dts_log.to_csv(os.path.join(outputdir,filename_log))
        
            # pick some samples to check
            if idx[0]%10==0:
                print '============================ idx=',idx[0],' ===== file =',os.path.basename(theinputfilename),'==================='
                print dts_log
                #spectrum_simulation.plot_spectrum(nofit=True)

