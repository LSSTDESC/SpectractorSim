
# coding: utf-8

# # Spectractor Simulation
# 
# Goal is to process a series of images in order to produce spectra
# 
# - author Sylvie Dagoret-Campagne
# - date : April 05th 2018
# - update : April 28th 2018
# 

import matplotlib.pyplot as plt
import sys
import os
import glob
import pandas as pd

PATH_SPECTRACTOR='../../Spectractor'
PATH_SPECTRACTORSIM='..'
PATH_GMAOMERRA='../merra2'

sys.path.append(PATH_SPECTRACTOR)
sys.path.append(PATH_SPECTRACTORSIM)

from spectractor import *
from spectractorsim import *


home=os.getenv('HOME')
path_data=os.path.join(home,'DATA/CTIODataJune2017_reduced_RG715_v2_prod1')

All_Subdirs=['data_28may17','data_29may17','data_30may17','data_31may17','data_01jun17','data_02jun17',
            'data_03jun17','data_04jun17','data_06jun17','data_08jun17','data_09jun17','data_10jun17',
            'data_12jun17','data_13jun17']

Flag_Photometric_Nights=[False,False,True,False,False,False,False,False,False,True,False,True,True,False]


# ### Select one directory to produce the data
idx_sel_subdir=2

#define the path of the reconstructed spectra
path_spectra=os.path.join(path_data,All_Subdirs[idx_sel_subdir])

# retrieve the list of files
search_string=os.path.join(path_spectra,'*.fits')
all_spectrafiles=glob.glob(search_string)
all_spectrafiles=sorted(all_spectrafiles)

# output directory
outputdir=os.path.join("./simspectra",All_Subdirs[idx_sel_subdir])
ensure_dir(outputdir)


#  Logbook
file_logbook_csv=os.path.join(PATH_SPECTRACTOR,'ctiofulllogbook_jun2017_v4.csv')
df_ctio_lbk=pd.read_csv(file_logbook_csv,sep=';')

print df_ctio_lbk.columns

df_ctio_lbk=df_ctio_lbk.reindex(columns=['date','P','T','RH','airmass','seeing','exposure','object','filter','disperser','focus','W','subdir','file']).set_index('date').sort_index()

df_ctio_lbk.head()

all_obs=df_ctio_lbk.loc[(df_ctio_lbk["subdir"]==All_Subdirs[idx_sel_subdir])].sort_index()
all_obs.head()



parameters.VERBOSE = False
parameters.DEBUG = False


## Simulation

for theinputfilename in all_spectrafiles:
    spectrum_simulation = SpectractorSim(theinputfilename,outputdir,lambdas=WL,pwv=5,ozone=300,aerosols=0.05)
    #spectrum_simulation.plot_spectrum(nofit=True)

