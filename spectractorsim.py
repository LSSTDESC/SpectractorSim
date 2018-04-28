"""
spectractorsim
=============----

author : Sylvie Dagoret-Campagne
affiliation : LAL/CNRS/IN2P3/FRANCE
Collaboration : DESC-LSST

Purpose : Simulate a series of spectra for each experimental spectra measured by auxiliary telescope.
Structure in parallel to Spectractor.
For each experimental spectra a fits file image is generated which holds all possible auxiliary telescope spectra
corresponding to different conditions in aerosols, pwv, and ozone. 

creation date : April 18th 
Last updaten : April 6th

"""

import numpy as np
import re
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.ticker import MaxNLocator

import sys,os
import copy
from astropy.io import fits
from astropy.coordinates import SkyCoord
import astropy.units as units
from astropy import constants as const

from scipy.interpolate import interp1d

sys.path.append("../Spectractor")

from tools import *
from dispersers import *
from targets import *
from images import *
from spectroscopy import *
import parameters 
#----------------------------------------------------------------------------
# where is spectractorsim
#----------------------------------------------------------------------------
spectractorsim_path = os.path.dirname(__file__)


#---------------------------------------------------------------------------
# Libraries to interface LibRadTran and CTIO 0.9m telescope transparencies
#-------------------------------------------------------------------------

import libsimulateTranspCTIOScattAbsAer as atmsim
import libCTIOTransm as ctio
#--------------------------------------------------------------------------
# Telescope parameter
#
#   The goal is to calculate the numerical factor to get spectra into ADU
#
#  the SED is supposed to be in flam units ie erg/s/cm^-2 per angtrom
#   however the binning is 10 A or 1 nm, the the SED has been multiplied by 10
#--------------------------------------------------------------------------
Tel_Diam=0.9*units.m                     # Diameter of the telescope
Tel_Surf=np.pi*Tel_Diam**2/4.            # collection surface of telescope
Time_unit=1*units.s                      # flux for 1 second
SED_unit=1*units.erg/units.s/(units.cm)**2/(units.nanometer)          # Units of SEDs in flam (erg/s/cm2/nm)
hc=const.h*const.c                        # h.c product of fontamental constants c and h 
wl_dwl_unit=(units.nanometer)**2          # lambda.dlambda  in wavelength in nm
g_elec=3.0                                # electronic gain : elec/ADU
g_disperser_ronchi=0.2                   # theoretical gain for order+1 : 20%
#Factor=2.1350444e11
Factor=(Tel_Surf*SED_unit*Time_unit*wl_dwl_unit/hc/g_elec*g_disperser_ronchi).decompose()



#------------------------------------------------------------------------
# Definition of data format for the atmospheric grid
#-----------------------------------------------------------------------------
WLMIN=parameters.LAMBDA_MIN # Minimum wavelength : PySynPhot works with Angstrom
WLMAX=parameters.LAMBDA_MAX # Minimum wavelength : PySynPhot works with Angstrom
WL=np.arange(WLMIN,WLMAX,1) # Array of wavelength in Angstrom


# specify parameters for the atmospheric grid

#aerosols
#NB_AER_POINTS=20
NB_AER_POINTS=2
AER_MIN=0.
AER_MAX=0.1

#ozone
#NB_OZ_POINTS=5
NB_OZ_POINTS=2
OZ_MIN=200
OZ_MAX=400

# pwv
#NB_PWV_POINTS=11
NB_PWV_POINTS=2
PWV_MIN=0.
PWV_MAX=10.

# definition of the grid
AER_Points=np.linspace(AER_MIN,AER_MAX,NB_AER_POINTS)
OZ_Points=np.linspace(OZ_MIN,OZ_MAX,NB_OZ_POINTS)
PWV_Points=np.linspace(PWV_MIN,PWV_MAX,NB_PWV_POINTS)

# total number of points
NB_ATM_POINTS=NB_AER_POINTS*NB_OZ_POINTS*NB_PWV_POINTS

#  column 0 : count number
#  column 1 : aerosol value
#  column 2 : pwv value
#  column 3 : ozone value
#  column 4 : data start 
#
index_atm_count=0
index_atm_aer=1
index_atm_pwv=2
index_atm_oz=3
index_atm_data=4

NB_atm_HEADER=5
NB_atm_DATA=len(WL)-1



MINFILESIZE=20000

            
#----------------------------------------------------------------------------------
class Atmosphere():
    """
    Atmosphere(): 
        class to simulate an atmospheric transmission calling libradtran
    Args:
        airmass (:obj:`float`): airmass of the target
        pressure (:obj:`float`): pressure of the atmosphere 
        temperature (:obj:`float`): temperature of the atmosphere 
    """
    
    #---------------------------------------------------------------------------
    def __init__(self,airmass,pressure,temperature):
        self.my_logger = parameters.set_logger(self.__class__.__name__)
        self.airmass = airmass
        self.pressure = pressure
        self.temperature = temperature
        self.transmission = lambda x: np.ones_like(x).astype(float)

    #---------------------------------------------------------------------------        
    def simulate(self,pwv,ozone,aerosols):
        """
        Args:
            pwv (:obj:`float`): pressure water vapor
            ozone (:obj:`float`): ozone quantity
            aerosols (:obj:`float`): VAOD Vertical Aerosols Optical Depth
        """
        # first determine the length
        if parameters.VERBOSE :
            self.my_logger.info('\n\tAtmospheric simulation with z=%4.2f, P=%4.2f, T=%4.2f, PWV=%4.2f, OZ=%4.2f, VAOD=%4.2f ' % (self.airmass,self.pressure,self.temperature,pwv,ozone,aerosols))
                 
        path,thefile = atmsim.ProcessSimulationaer(self.airmass,pwv,ozone,aerosols,self.pressure)
        data = np.loadtxt(os.path.join(path,thefile))
        wl = data[:,0]
        atm = data[:,1]
        self.transmission = interp1d(wl,atm,kind='linear')   
                    
        return self.transmission
    #---------------------------------------------------------------------------  
    def plot_transmission(self):
        plt.figure()
        plt.plot(WL,self.transmission(WL),label='z=%4.2f, P=%4.2f, T=%4.2f' % (self.airmass,self.pressure,self.temperature))
        plt.grid()
        plt.xlabel("$\lambda$ [nm]")
        plt.ylabel("Atmospheric transparency")
        plt.legend()
        plt.show()
        
#----------------------------------------------------------------------------------
class AtmosphereGrid(Atmosphere):
    """
    Atmosphere(): 
        class to simulate series of atmospheres calling libradtran
    Args:
        airmass (:obj:`float`): airmass of the target
        pressure (:obj:`float`): pressure of the atmosphere 
        temperature (:obj:`float`): temperature of the atmosphere 
        filenamedata (:obj:`strt`): XXXXXXXXXX     
    """
    
    #---------------------------------------------------------------------------
    def __init__(self,airmass,pressure,temperature,filenamedata):
        Atmosphere.__init__(self,airmass,pressure,temperature)
        self.my_logger = parameters.set_logger(self.__class__.__name__)
        self.filenamedata=filenamedata          
        # create the numpy array that will contains the atmospheric grid    
        self.atmgrid=np.zeros((NB_ATM_POINTS+1,NB_atm_HEADER+NB_atm_DATA))
        self.atmgrid[0,index_atm_data:]=WL
        self.header=fits.Header()
    #---------------------------------------------------------------------------        
    def compute(self):
        # first determine the length
        if parameters.VERBOSE or parameters.DEBUG:
            self.my_logger.info('\n\tAtmosphere simulations for z=%4.2f, P=%4.2f, T=%4.2f, for data-file=%s ' % (self.airmass,self.pressure,self.temperature,self.filenamedata))
            
        count=0
        for  aer in AER_Points:
            for pwv in PWV_Points:
                for oz in OZ_Points:
                    count+=1
                    # fills headers info in the numpy array
                    self.atmgrid[count,index_atm_count]=count
                    self.atmgrid[count,index_atm_aer]=aer
                    self.atmgrid[count,index_atm_pwv]=pwv
                    self.atmgrid[count,index_atm_oz]=oz
                    transmission = self.simulate(pwv,oz,aer)
                    transm=transmission(WL)   
                    self.atmgrid[count,index_atm_data:]=transm    # each of atmospheric transmission
                    
        return self.atmgrid
    #---------------------------------------------------------------------------  
    def plot_transmission(self):
        plt.figure()
        counts=self.atmgrid[1:,index_atm_count]
        for count in counts:
            plt.plot(WL,self.atmgrid[int(count),index_atm_data:])
        plt.grid()
        plt.xlabel("$\lambda$ [nm]")
        plt.ylabel("Atmospheric transmission")
        plt.title("Atmospheric variations")
        plt.show()
    #---------------------------------------------------------------------------   
    def plot_transm_img(self):
        plt.figure()
        img=plt.imshow(self.atmgrid[1:,index_atm_data:],origin='lower',cmap='jet')
        plt.grid(True)
        plt.xlabel("$\lambda$ [nm]")
        plt.ylabel("Simulation number")
        plt.title(" Atmospheric variations")
        cbar=plt.colorbar(img)
        cbar.set_label('Atmospheric transmission')
        plt.show()
    #---------------------------------------------------------------------------    
    def savefile(self,filename=""):
             
        hdr = fits.Header()
               
        if filename != "" :
            self.filename = filename
        
        if self.filename=="":
            infostring='\n\t Atmosphere:savefile no input file given ...'
            self.my_logger.info(infostring)
            return
        else:
            hdr['ATMSIM'] = "libradtran"
            hdr['SIMVERS'] = "2.0.1"
            hdr['DATAFILE']=self.filenamedata
            hdr['SIMUFILE']=os.path.basename(self.filename)
            
            hdr['AIRMASS'] = self.airmass
            hdr['PRESSURE'] = self.pressure
            hdr['TEMPERAT'] = self.temperature
            hdr['NBATMPTS'] = NB_ATM_POINTS
        
            hdr['NBAERPTS'] = NB_AER_POINTS
            hdr['AERMIN'] = AER_MIN
            hdr['AERMAX'] = AER_MAX

            hdr['NBPWVPTS'] = NB_PWV_POINTS
            hdr['PWVMIN'] = PWV_MIN
            hdr['PWVMAX'] = PWV_MAX
        
            hdr['NBOZPTS'] = NB_OZ_POINTS
            hdr['OZMIN'] = OZ_MIN
            hdr['OZMAX'] = OZ_MAX

            hdr['AER_PTS'] =np.array_str(AER_Points)
            hdr['PWV_PTS'] =np.array_str(PWV_Points)
            hdr['OZ_PTS'] =np.array_str(OZ_Points)
            hdr['NBWLBIN'] = WL.size
            hdr['WLMIN'] = WLMIN
            hdr['WLMAX'] = WLMAX
    
            hdr['IDX_CNT']=index_atm_count
            hdr['IDX_AER']=index_atm_aer
            hdr['IDX_PWV']=index_atm_pwv
            hdr['IDX_OZ']=index_atm_oz
            hdr['IDX_DATA']=index_atm_data
    
            if parameters.VERBOSE:
                print hdr
    
            hdu = fits.PrimaryHDU(self.atmgrid,header=hdr)
            hdu.writeto(self.filename,overwrite=True)
            if parameters.VERBOSE or parameters.DEBUG:
                self.my_logger.info('\n\tAtmosphere.save atm-file=%s' % (self.filename))
                
            return hdr
    #---------------------------------------------------------------------------   
    def loadfile(self,filename):
             
        if filename != "" :
            self.filename = filename
               
        
        if self.filename=="":
            infostring='\n\t Atmosphere:loadfile no input file given ...'
            self.my_logger.info(infostring)
 
            return
        else:
        
            hdu= fits.open(self.filename)
            hdr=hdu[0].header
       
            #hdr['ATMSIM'] = "libradtran"
            #hdr['SIMVERS'] = "2.0.1"
            self.filenamedata=hdr['DATAFILE']
            #hdr['SIMUFILE']=os.path.basename(self.filename)
            
            self.airmass=hdr['AIRMASS'] 
            self.pressure=hdr['PRESSURE']
            self.temperature=hdr['TEMPERAT']
            
            # hope those are the same parameters : TBD !!!!
            NB_ATM_POINTS=hdr['NBATMPTS']
        
            NB_AER_POINTS=hdr['NBAERPTS'] 
            AER_MIN=hdr['AERMIN']  
            AER_MAX=hdr['AERMAX'] 

            NB_PWV_POINTS=hdr['NBPWVPTS'] 
            PWV_MIN=hdr['PWVMIN'] 
            PWV_MAX=hdr['PWVMAX'] 
        
            NB_OZ_POINTS=hdr['NBOZPTS'] 
            OZ_MIN=hdr['OZMIN'] 
            OZ_MAX=hdr['OZMAX'] 
            
            AER_Points=np.linspace(AER_MIN,AER_MAX,NB_AER_POINTS)
            OZ_Points=np.linspace(OZ_MIN,OZ_MAX,NB_OZ_POINTS)
            PWV_Points=np.linspace(PWV_MIN,PWV_MAX,NB_PWV_POINTS)

            #hdr['AER_PTS'] =np.array_str(AER_Points)
            #hdr['PWV_PTS'] =np.array_str(PWV_Points)
            #hdr['OZ_PTS'] =np.array_str(OZ_Points)
            
            NBWLBINS= hdr['NBWLBIN']
            WLMIN= hdr['WLMIN']
            WLMAX= hdr['WLMAX']
    
            index_atm_count=hdr['IDX_CNT']
            index_atm_aer=hdr['IDX_AER']
            index_atm_pwv=hdr['IDX_PWV']
            index_atm_oz=hdr['IDX_OZ']
            index_atm_data=hdr['IDX_DATA']
    
            self.atmgrid=np.zeros((NB_ATM_POINTS+1,NB_atm_HEADER+NB_atm_DATA))
    
            self.atmgrid[:,:]=hdu[0].data[:,:]
           
            if parameters.VERBOSE or parameters.DEBUG:
                self.my_logger.info('\n\tAtmosphere.load atm-file=%s' % (self.filename))
                
            return self.atmgrid,self.header
        #---------------------------------------------------------------------------
        
 
  
#----------------------------------------------------------------------------------
class TelescopeTransmission():
    """
    TelescopeTransmission : Transmission of the telescope
    - mirrors
    - throughput
    - QE
    - Filter
    
    """
    #---------------------------------------------------------------------------
    def __init__(self,filtername=""):
        """
        Args:
        filename (:obj:`str`): path to the data filename (for info only)
        """
    
        self.my_logger = parameters.set_logger(self.__class__.__name__)
        self.filtername = filtername
        self.load_transmission()

    #---------------------------------------------------------------------------    
    def load_transmission(self):
        """
        load_transmission(self) :
            load the telescope transmission
            return the total telescope transmission, disperser excluded, 
                as a fnction of the wavelength in Angstrom
        """
        
        # defines the datapath relative to the Spectractor sim path
        datapath=os.path.join(spectractorsim_path,"CTIOThroughput")
        
        # QE
        wl,qe=ctio.Get_QE(datapath)
        self.qe=interp1d(wl,qe,kind='linear',bounds_error=False,fill_value=0.) 
        
        #  Throughput
        wl,trt=ctio.Get_Throughput(datapath)
        self.to=interp1d(wl,trt,kind='linear',bounds_error=False,fill_value=0.)
        
        # Mirrors 
        wl,trm=ctio.Get_Mirror(datapath)
        self.tm=interp1d(wl,trm,kind='linear',bounds_error=False,fill_value=0.) 
          
        # Filter RG715
        wl,trg=ctio.Get_RG715(datapath)
        self.tfr=interp1d(wl,trg,kind='linear',bounds_error=False,fill_value=0.)
        
        # Filter FGB37
        wl,trb=ctio.Get_FGB37(datapath)
        self.tfb=interp1d(wl,trb,kind='linear',bounds_error=False,fill_value=0.)
            
        if self.filtername == "RG715" :
            TF=self.tfr
        elif self.filtername =="FGB37":
            TF=self.tfb
        else:
            TF=lambda x: np.ones_like(x).astype(float)
            
        self.tf=TF
        
        self.transmission=lambda x: self.qe(x)*self.to(x)*(self.tm(x)**2)*self.tf(x)     
        return self.transmission
    #---------------------------------------------------------------------------    
    def plot_transmission(self,xlim=None):
        """
        plot_transmission()
            plot the various transmissions of the instrument
        """
        plt.figure()
        plt.plot(WL,self.qe(WL),'b-',label='qe')
        plt.plot(WL,self.to(WL),'g-',label='othr')
        plt.plot(WL,self.tm(WL),'y-',label='mirr')
        plt.plot(WL,self.tf(WL),'k-',label='filt')
        plt.plot(WL,self.tfr(WL),'k:',label='RG715')
        plt.plot(WL,self.tfb(WL),'k--',label='FGB37')
        plt.plot(WL,self.transmission(WL),'r-',lw=2,label='tot')
        plt.legend()
        plt.grid()
        plt.xlabel("$\lambda$ [nm]")
        plt.ylabel("Transmission")
        plt.title("Telescope transmissions")
#----------------------------------------------------------------------------------        
               
        
        
                
#----------------------------------------------------------------------------------
class SpectrumSimulation(Spectrum):
    """ 
    SpectrumSim class used to store information and methods relative to spectrum simulation.
    It inherit from the class Spectrum (in Spectractor/Spectroscopy.py)
    """
    #---------------------------------------------------------------------------
    def __init__(self,spectrum,atmosphere,telescope,disperser):
        """
        Args:
            filename (:obj:`str`): path to the image
        """
        Spectrum.__init__(self)
        for k,v in spectrum.__dict__.items():
            self.__dict__[k] = copy.copy(v)
        self.my_logger = parameters.set_logger(self.__class__.__name__)        
        self.disperser = disperser
        self.telescope = telescope        
        self.atmosphere = atmosphere
        self.lambdas = None
        self.data = None
        self.err = None
    #----------------------------------------------------------------------------    
    def simulate_without_atmosphere(self,lambdas):
        self.lambdas = lambdas
        self.err=np.zeros(len(lambdas))
        self.lambda_binwidths = np.gradient(lambdas)
        all_transm = self.disperser.transmission(lambdas)
        all_transm *= self.telescope.transmission(lambdas)
        all_transm *= self.target.sed(lambdas)
        all_transm *= self.lambdas*self.lambda_binwidths         
        return all_transm
    #----------------------------------------------------------------------------    
    def simulate(self,lambdas):
        all_transm = self.simulate_without_atmosphere(lambdas)
        all_transm *= self.atmosphere.transmission(lambdas)
        self.data = all_transm*Factor
        return all_transm
    #---------------------------------------------------------------------------            
                
#----------------------------------------------------------------------------------
class SpectrumSimGrid():
    """ SpectrumSim class used to store information and methods
    relative to spectrum simulation.
    """
    #---------------------------------------------------------------------------
    def __init__(self,spectrum,atmgrid,telescope,disperser,target,header,filename=""):
        """
        Args:
            filename (:obj:`str`): path to the image
        """
        self.my_logger = parameters.set_logger(self.__class__.__name__)

        self.spectrum = spectrum
        self.header = spectrum.header
        self.disperser = disperser
        self.target = target
        self.telescope = telescope
        
        self.atmgrid = atmgrid
        self.lambdas = atmgrid[0,index_atm_data:]
        self.lambda_binwidths = np.gradient(self.lambdas)
        self.spectragrid = None

        self.filename=""
        if filename != "" :
            self.filename = filename
            self.load_spectrum(filename)

        if parameters.VERBOSE :
            print self.header

    #----------------------------------------------------------------------------    
    def compute(self):
        sim = SpectrumSimulation(self.spectrum,self.atmgrid,self.telescope,self.disperser)
        # product of all sed and transmission except atmosphere
        all_transm = sim.simulate_without_atmosphere(self.lambdas)
        # copy atmospheric grid parameters into spectra grid
        self.spectragrid = np.zeros_like(self.atmgrid) 
        self.spectragrid[0,index_atm_data:]=self.lambdas
        self.spectragrid[:,index_atm_count:index_atm_data]=self.atmgrid[:,index_atm_count:index_atm_data] 
        # Is broadcasting working OK ?
        self.spectragrid[1:,index_atm_data:]=self.atmgrid[1:,index_atm_data:]*all_transm*Factor
         
        return self.spectragrid
    #---------------------------------------------------------------------------
    def plot_spectra(self):
        plt.figure()
        counts=self.spectragrid[1:,index_atm_count]
        for count in counts:
            plt.plot(WL,self.spectragrid[int(count),index_atm_data:])
        plt.grid()
        plt.xlabel("$\lambda$ [nm]")
        plt.ylabel("Flux [ADU/s]")
        plt.title("Spectra for Atmospheric variations")
        plt.show()
    #---------------------------------------------------------------------------   
    def plot_spectra_img(self):
        plt.figure()
        img=plt.imshow(self.spectragrid[1:,index_atm_data:],origin='lower',cmap='jet')
        plt.xlabel("$\lambda$ [nm]")
        plt.ylabel("Simulation number")
        plt.title("Spectra for atmospheric variations")
        cbar=plt.colorbar(img)
        cbar.set_label("Flux [ADU/s]")
        plt.grid(True)
        plt.show()
    #---------------------------------------------------------------------------  
    def save_spectra(self,filename):
                   
        if filename != "" :
            self.filename = filename
        
        if self.filename=="":
            return
        else:
         
            hdu = fits.PrimaryHDU(self.spectragrid,header=self.header)
            hdu.writeto(self.filename,overwrite=True)
            if parameters.VERBOSE or parameters.DEBUG:
                self.my_logger.info('\n\tSPECTRA.save atm-file=%s' % (self.filename))
    #---------------------------------------------------------------------------            
   
#----------------------------------------------------------------------------------        


#----------------------------------------------------------------------------------
def SpectractorInit(filename,outputdir):
    
    """ SpectractorInit
    Main function to simulate several spectra 
    A grid of spectra will be produced for a given target, airmass and pressure

    Args:
        filename (:obj:`str`): filename of the image (data)
        outputdir (:obj:`str`): path to the output directory
        
    """
    my_logger = parameters.set_logger(__name__)
    my_logger.info('\n\tStart SPECTRACTORSIM initialisation')
    # Load data spectrum
    spectrum = Spectrum(filename)
    
    # TELESCOPE TRANSMISSION
    # ------------------------
    telescope=TelescopeTransmission(spectrum.filter)    
    if parameters.VERBOSE:
        infostring='\n\t ========= Telescope transmission :  ==============='
        my_logger.info(infostring)
        telescope.plot_transmission()
        
    # DISPERSER TRANSMISSION
    # ------------------------
    disperser = Hologram(label=spectrum.disperser)
    if parameters.VERBOSE:
        infostring='\n\t ========= Disperser transmission :  ==============='
        my_logger.info(infostring)
        disperser.plot_transmission()
    
    # STAR SPECTRUM
    # ------------------------
    target = spectrum.target
    if parameters.VERBOSE:
        infostring='\n\t ========= SED : %s  ===============' % target.label
        my_logger.info(infostring)
        target.plot_spectra()

    return spectrum, telescope, disperser, target 
    
       
#----------------------------------------------------------------------------------
def SpectractorSimGrid(filename,outputdir):
    
    """ SpectractorSimGrid
    Main function to simulate several spectra 
    A grid of spectra will be produced for a given target, airmass and pressure

    Args:
        filename (:obj:`str`): filename of the image (data)
        outputdir (:obj:`str`): path to the output directory
        
    """
    my_logger = parameters.set_logger(__name__)
    my_logger.info('\n\tStart SPECTRACTORSIMGRID')
    # Initialisation
    spectrum, telescope, disperser, target = SpectractorInit(filename,outputdir)
    # Set output path
    ensure_dir(outputdir)
    # extract the basename : simimar as os.path.basename(file)
    base_filename = filename.split('/')[-1] 
    output_filename=os.path.join(outputdir,base_filename.replace('spectrum','spectrasim'))
    output_atmfilename=os.path.join(outputdir,base_filename.replace('spectrum','atmsim')) 
    
    # SIMULATE ATMOSPHERE GRID
    # ------------------------
    airmass = spectrum.header['AIRMASS']
    pressure = spectrum.header['OUTPRESS']
    temperature = spectrum.header['OUTTEMP']
    atm = AtmosphereGrid(airmass,pressure,temperature,filename)
    
    # test if file already exists
    #if os.path.exists(output_atmfilename) and os.path.getsize(output_atmfilename)>MINFILESIZE:       
    #    filesize= os.path.getsize(output_atmfilename)
    #    infostring=" atmospheric simulation file %s of size %d already exists, thus load it ..." % (output_atmfilename,filesize)
    #    my_logger.info(infostring)
    #    atmgrid,header=atm.loadfile(output_atmfilename)
    #else:
    atmgrid = atm.compute()
    header = atm.savefile(filename=output_atmfilename)
    atmsim.CleanSimDir()    
    if parameters.VERBOSE:
        infostring='\n\t ========= Atmospheric simulation :  ==============='
        my_logger.info(infostring)
        atm.plot_transmission()   # plot all atm transp profiles
        atm.plot_transm_img()   # plot 2D image summary of atm simulations
    
    # SPECTRA-GRID  
    #-------------   
    # in any case we re-calculate the spectra in case of change of transmission function
    spectra=SpectrumSimGrid(spectrum,atmgrid,telescope,disperser,target,header)
    spectragrid=spectra.compute()
    spectra.save_spectra(output_filename)    
    if parameters.VERBOSE:
        infostring='\n\t ========= Spectra simulation :  ==============='
        spectra.plot_spectra()
        spectra.plot_spectra_img()
    #--------------------------------------------------------------------------- 
    
       
#----------------------------------------------------------------------------------
def SpectractorSim(filename,outputdir,lambdas,pwv=5,ozone=300,aerosols=0.05,overwrite=True):
    
    """ SpectractorSim
    Main function to simulate several spectra 
    A grid of spectra will be produced for a given target, airmass and pressure

    Args:
        filename (:obj:`str`): filename of the image (data)
        outputdir (:obj:`str`): path to the output directory
        pwv (:obj:`float`): pressure water vapor
        ozone (:obj:`float`): ozone quantity
        aerosols (:obj:`float`): VAOD Vertical Aerosols Optical Depth        
    """
    my_logger = parameters.set_logger(__name__)
    my_logger.info('\n\tStart SPECTRACTORSIM')
    # Initialisation
    spectrum, telescope, disperser, target = SpectractorInit(filename,outputdir)

    # SIMULATE ATMOSPHERE
    # -------------------
    airmass = spectrum.header['AIRMASS']
    pressure = spectrum.header['OUTPRESS']
    temperature = spectrum.header['OUTTEMP']
    atmosphere = Atmosphere(airmass,pressure,temperature)
    atmosphere.simulate(pwv,ozone,aerosols)  
    
    if parameters.VERBOSE:
        infostring='\n\t ========= Atmospheric simulation :  ==============='
        my_logger.info(infostring)
        infostring="\n\t outputdir = "+outputdir
        my_logger.info(infostring)
        
        atmosphere.plot_transmission()   # plot all atm transp profiles
    
    # SPECTRUM SIMULATION  
    #--------------------
    spectrum_simulation = SpectrumSimulation(spectrum,atmosphere,telescope,disperser)
    spectrum_simulation.simulate(lambdas)   
    
    if parameters.VERBOSE:
        infostring='\n\t ========= Spectra simulation :  ==============='
        spectrum_simulation.plot_spectrum(nofit=True)
        
    # SAVE SPECTRUM
    #------------------   
    if outputdir != None:
        
        if parameters.VERBOSE:
            infostring="\n\t Simulated spectrum will be saved in outputdir = "+outputdir
            my_logger.info(infostring)
       
        # extract the basename : simimar as os.path.basename(file)
        base_filename = filename.split('/')[-1]  # get "reduc_20170530_213.fits"
        tag_filename=base_filename.split('_')[0] # get "reduc_"
        search_str ='^%s_(.*)' % (tag_filename)  # get "^reduc_(.*)"
        root_filename=re.findall(search_str,base_filename)[0]   # get "20170530_213.fits'
    
        output_filename='specsim_'+root_filename # get "spectrasim_20170530_213.fits" 
        output_filename = os.path.join(outputdir,output_filename)
    
        if parameters.VERBOSE:
            infostring='output filename ='+output_filename 
            my_logger.info(infostring)
        
        spectrum_simulation.save_spectrum(output_filename,overwrite=overwrite)
        
    return spectrum_simulation
    #--------------------------------------------------------------------------- 
    
       
    
    
#----------------------------------------------------------------------------------
#  START SPECTRACTORSIM HERE !
#----------------------------------------------------------------------------------


if __name__ == "__main__":
    #import commands, string,  time
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-d", "--debug", dest="debug",action="store_true",
                      help="Enter debug mode (more verbose and plots).",default=False)
    parser.add_option("-v", "--verbose", dest="verbose",action="store_true",
                      help="Enter verbose (print more stuff).",default=False)
    parser.add_option("-o", "--output_directory", dest="output_directory", default="test/",
                      help="Write results in given output directory (default: ./tests/).")
    (opts, args) = parser.parse_args()

    parameters.VERBOSE = opts.verbose
    
    if opts.debug:
        parameters.DEBUG = True
        parameters.VERBOSE = True
        

    filename="notebooks/fits/reduc_20170528_060_spectrum.fits"
    
    
    spectrum_simulation = SpectractorSim(filename,opts.output_directory,lambdas=WL,pwv=5,ozone=300,aerosols=0.05)
    spectrum_simulation.plot_spectrum(nofit=True)
    #SpectractorSimGrid(filename,opts.output_directory)
    
    
