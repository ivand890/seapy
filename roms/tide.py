#!/usr/bin/env python
"""
  tide.py

  Methods for working tidal forcing files in ROMS

  Written by Brian Powell on 04/05/16
  Copyright (c)2016 University of Hawaii under the BSD-License.
"""


import numpy as np
import netCDF4
import seapy
import datetime
from warnings import warn


def load_forcing(filename):
    """
    Load a tidal forcing file into a dictionary

    Parameters
    ----------
    filename: 


    Returns
    -------
    dict:
      Dictionary of the tidal forcing information with keys:
       Eamp : SSH amplitdue
       Ephase : SSH phase (radians)
       Cmajor : velocity major ellipse
       Cminor : velocity minor ellipse
       Cphase : velocity ellipse phase (radians)
       Cangle : velocity ellipse angle (radians)
       tide_start : datetime of the tide reference
       tides  : list of the tides
    """
    nc = seapy.netcdf(tide_file)
    frc = {}
    frc['Eamp'] = nc.variables['tide_Eamp'][:]
    frc['Ephase'] = np.radians(nc.variables['tide_Ephase'][:])
    frc['Cmajor'] = nc.variables['tide_Cmajor'][:]
    frc['Cminor'] = nc.variables['tide_Cminor'][:]
    frc['Cphase'] = np.radians(nc.variables['tide_Cphase'][:])
    frc['Cangle'] = np.radians(nc.variables['tide_Cangle'][:])
    start_str = getattr(nc, 'tide_start', None) or \
        getattr(nc, 'base_date', None)
    tides = getattr(nc, 'tidal_constituents', None) or \
        getattr(nc, 'tides', None)
    frc['tides'] = tides.upper().split(", ")
    frc['tide_start'] = None
    nc.close()
    if start_str:
        try:
            frc['tide_start'] = datetime.datetime.strptime(
                re.sub('^.*since\s*', '', start_str),
                "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    return frc


def tide_error(his_file, tide_file):
    """
    Calculates the tidal error for each point given a model history and the
    tidal file used 

    Parameters
    ----------
    his_file : string,
      String of history file location. Can be multiple files using wildcard
    tide_file: string,
      String of tidal file location

    Returns
    -------
      tide_error : masked_array,
        Array containing the tidal error at each point, with land points masked 

    """
    g = seapy.model.asgrid(his_file)
       
    # Load tidal file data
    frc = load_forcing(tide_file)
    
    #Calculate tidal error for each point
    nc = seapy.netcdf(his_file)
    times = seapy.roms.get_time(nc)
    tide_error = ma.masked_array(np.zeros((g.mask_rho.shape)),mask=np.abs(g.mask_rho-1))
    for i in seapy.progressbar.progress(range(g.ln)):
        for j in range(g.lm):
            if not tide_error.mask[i,j]:
                z = nc.variables['zeta'][:,i,j]
                t_ap = pack_amp_phase(frc['tides'], frc['Eamp'][:,i,j], frc['Ephase'][:, i,j])
                mout = fit(times,z,tides=tfile_tides,lat=g.lat_rho[i,j],tide_start=tide_start)
                for c in t_ap:
                    m = mout['major'][c]
                    t = t_ap[c]
                    tide_error[i,j] += 0.5*(m.amp**2 + t.amp**2) - m.amp*t.amp*np.cos(m.phase-t.phase)
                tide_error[i,j] = np.sqrt(tide_error[i,j])
    nc.close()
    
    return tide_error