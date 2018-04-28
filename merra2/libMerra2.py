#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sat Apr 28 17:52:05 2018

@author: dagoret
"""

import numpy as np
import pandas as pd
import sys
import os

libmerra2_path = os.path.dirname(__file__)

# remove data_26may because all times are creazy time
# supressed'data_26may17'
All_Subdirs=['data_28may17','data_29may17','data_30may17','data_31may17','data_01jun17','data_02jun17',
            'data_03jun17','data_04jun17','data_06jun17','data_08jun17','data_09jun17','data_10jun17',
            'data_12jun17','data_13jun17']

Flag_Photometric_Nights=[False,False,True,False,False,False,False,False,False,True,False,True,True,False]


#------------------------------------------------------------------------------------
def GetStartStoptime(df_ctio_subdir):
    """
    Retrieve the start and stop time of a subdir dataset
    input: df_ctio_subdir dataset of CTIO data
    output:
        start_time
        stop_time
    """
    all_datetime_ctio_subdir=pd.to_datetime(df_ctio_subdir.index.get_values())
    start_time=all_datetime_ctio_subdir[0]
    stop_time=all_datetime_ctio_subdir[-1]
    return start_time,stop_time  
#------------------------------------------------------------------------------------
def GetAtmosphericParameters(timestamp0,df_merra2):
    """
    GetAtmosphericParameters(timestamp0,df_merra2) :
     return closest time atmospheric parameters from merra dataset at timestamp0
    
    input arg:
    - timestamp0 : timestamp of the CTIO image in pd.DateTime type
    - df_merra2  : pandas dataset holding all atmospheric parameters indexed by time
    
    where :
    "ps","pwv","ozone" are estimated every hours
    'TOTEXTTAU','TOTANGSTR','TOTSCATAU','TAUTOT','TAUHGH','TAUMID','TAULOW' are estimated ever hour at hour and a half 
    
    then  df_merra2 is split into two datasets in which there are no NA value.
    The estimated value the closest in time are returned
    
    return:
        - ps : presure in hPa from dataset1
        - pwv : Precipitable Water vapour in mm from dataset1
        - ozone : Ozone in Dobson Unit in dataset1 
        - aer   : vertical aerosol optical depth at 550 nm in dataset2
        - clouds : clouds in vertical depth
        - deltat1,deltat2  : time delay wrt timestamp
    
    """
    
    # decode the time form timestamp
    year0=timestamp0.year
    month0=timestamp0.month
    day0=timestamp0.days_in_month
    hour0=timestamp0.hour
    minu0=timestamp0.minute
    
    # remove NA in rows and split in 2 datasets, dataset1,dataset2 without NA 
    # datset1 with ps, pwv ozone 
    dataset1_m2=df_merra2.dropna(axis=0,how='all',subset=["ps","pwv","ozone"]).loc[:, 'ps':'ozone']
    # datset2 with aerosols and clouds
    dataset2_m2=df_merra2.dropna(axis=0,how='all',subset=['TOTEXTTAU','TOTANGSTR','TOTSCATAU','TAUTOT','TAUHGH','TAUMID','TAULOW']).loc[:,'TOTEXTTAU':'TAULOW']
    
    
    # convert the string into timestamp
    #-------------------------------------
    all_datetime1_m2=pd.to_datetime(dataset1_m2.index.get_values())
    all_datetime2_m2=pd.to_datetime(dataset2_m2.index.get_values())
    
   
    # get time difference between timestamp = timestamp-merra2-timestamp-ctio
    #---------------------------------------
    deltat1=(all_datetime1_m2-timestamp0).total_seconds()
    deltat2=(all_datetime2_m2-timestamp0).total_seconds()
    
    delays1=np.abs(deltat1)
    idx1=np.where(delays1==delays1.min())[0][0]
    
    delays2=np.abs(deltat2)
    idx2=np.where(delays2==delays2.min())[0][0]
    
    if False:
        print 'deltat1 :' ,deltat1[idx1], pd.Timedelta(deltat1[idx1],unit='s')
        print dataset1_m2.iloc[idx1,:]
        
        print 'deltat2 :' ,deltat2[idx2],pd.Timedelta(deltat2[idx2],unit='s')
        print dataset2_m2.iloc[idx2,:]
        
    ps=dataset1_m2.iloc[idx1]["ps"]/100. # convert Pa into hecto-Pa
    pwv=dataset1_m2.iloc[idx1]["pwv"]
    ozone=dataset1_m2.iloc[idx1]["ozone"]
    aer=dataset2_m2.iloc[idx2]["TOTEXTTAU"]
    clouds=dataset2_m2.iloc[idx2]["TAUTOT"]
    
    if False:
        print 'idx1=',idx1,' P=',ps,' pwv=',pwv,' ozone =',ozone
        print 'idx2=',idx2,' aer=',aer, ' , clouds = ',clouds
    
    return ps,pwv,ozone,aer,clouds,deltat1[idx1]/60.,deltat2[idx2]/60.  

                        
#--------------------------------------------------------------------------------------
#     START HERE    
#--------------------------------------------------------------------------------------

if __name__ == "__main__":
    
    # MERRA2 file
    file_merra2='MERRA2_2017_M2I1NXASM_M2T1NXAER_M2T1NXRAD_ctio_AllYear.csv'
    df_merra2=pd.read_csv(file_merra2,index_col=0)
    df_merra2.index.name='time'
    
    # LOGBOOK File
    file_logbook_ctio='ctiofulllogbook_jun2017_v4.csv'
    df_ctio=pd.read_csv(file_logbook_ctio,sep=';')
    df_ctio=df_ctio.reindex(columns=['date','P','T','RH','airmass','seeing','exposure','object','filter','disperser',
                                 'focus','W','subdir','file']).set_index('date').sort_index()
    all_datetime_ctio=pd.to_datetime(df_ctio.index.get_values())
    
    
    # Select a subdir
    subdir_sel_idx=2
    # Extract the dataset corresponding to that subdir
    df_ctio_subdir=df_ctio[df_ctio["subdir"]==All_Subdirs[subdir_sel_idx]]
    
    # test the function GetStartStoptime
    print GetStartStoptime(df_ctio_subdir)
    
    # DateTime of the subdir
    mydates=pd.to_datetime(df_ctio_subdir.index.get_values())
    
    # select one date
    one_mydates=mydates[5]
    
    # test GetAtmosphericParameters()
    print GetAtmosphericParameters(one_mydates,df_merra2)
    
    for thedate in mydates:
        print GetAtmosphericParameters(thedate,df_merra2)
    
    
    
    