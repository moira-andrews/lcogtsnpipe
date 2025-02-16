from scipy.optimize import fsolve # root
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u
import numpy as np
from scipy import stats, odr
import matplotlib.pyplot as plt
import warnings
import lsc
import os
from pyraf import iraf

with warnings.catch_warnings(): # so cronic doesn't email on the "experimental" warning
    warnings.simplefilter('ignore')
    from astroquery.sdss import SDSS

def get_other_filters(filename, match_by_site=False):
    if match_by_site:
        tel_join = '''photlco AS p1 JOIN telescopes AS t1 ON p1.telescopeid = t1.id,
                      photlco AS p2 JOIN telescopes AS t2 ON p2.telescopeid = t2.id'''
        is_match = 't1.shortname = t2.shortname'
    else:
        tel_join = 'photlco AS p1, photlco AS p2'
        is_match = 'p1.telescopeid = p2.telescopeid'
    query = '''SELECT DISTINCT p2.filter FROM {tel_join}
               WHERE p1.filename='{filename}'
               AND p2.quality=127
               AND p1.dayobs=p2.dayobs
               AND p1.targetid=p2.targetid
               AND {is_match}'''.format(tel_join=tel_join, filename=filename, is_match=is_match)
    result = lsc.mysqldef.query([query], lsc.conn)
    other_filters = {lsc.sites.filterst1[row['filter']] for row in result}
    return other_filters

def limmag(img, zeropoint=0, Nsigma_limit=3, _fwhm = 5):
    image = fits.open(img)
    hdr = image[0].header
    data = image[0].data
    #_sky = np.median(data)
    _skynoise = 1.4826 * np.median(np.abs(data - np.median(data)))
    _exptime = lsc.util.readkey3(hdr, 'exptime')
    _gain = lsc.util.readkey3(hdr, 'gain')
    _readnoise = lsc.util.readkey3(hdr, 'ron')
    _pixelscale = lsc.util.readkey3(hdr, 'pixscale')
    _radius = float(_fwhm) / float(_pixelscale)
    if _radius and _gain and _skynoise:
        print _skynoise, _gain, _radius
        #    mag = calc_limit_mag(Nsigma_limit, _sky, _gain, _readnoise, _exptime, zeropoint, _radius)
        limit_counts = fsolve(snr_helper, np.median(data), args = [Nsigma_limit, _readnoise, _gain, _skynoise,_radius])[0]
        mag = -2.5 * np.log10(limit_counts / _exptime) + zeropoint
    else:
        mag = 9999
    return mag

def snr_equation(counts, Nsigma_limit, rdnoise, gain, skynoise,radius):
    """
    Invert the signal to noise equation and compare to the limiting number of sigma.
    :param counts: Source Counts in ADU
    :param Nsigma_limit: Number of sigma limit (e.g. 5-sigma limit)
    :param rdnoise: Read noise in electrons
    :param gain: Gain (electrons / ADU)
    :param sky: Sky value in ADU (likely the median of an image)
    :return: Signal / Noise difference from the limiting sigma
    """
    area = np.pi * radius**2 
    snr = counts * gain - Nsigma_limit * (counts * gain + (skynoise * gain)**2 * area + rdnoise**2 * area) ** 0.5
    return snr

def snr_helper(counts, extra):
    """
    Helper function to interface with scipy.optimize.root
    :param counts: Object counts for the S/N calculation
    :param extra: Other parameters to pass to the snr function
    :return: Signal / Noise difference from the limiting sigma
    """
    return snr_equation(counts, *extra)

#def calc_limit_mag(Nsigma_limit, sky, gain, readnoise, exptime, zeropoint,radius):
#    """
#    Calculate a limiting magnitude of an image
#    :param Nsigma_limit: Number of sigma limit (e.g. 5-sigma limit)
#    :param sky: sky value in ADU (like the median of an image)
#    :param gain: Gain (electrons / ADU)
#    :param readnoise: Read Noise in electrons
#    :param exptime: Exposure time in seconds
#    :param zeropoint: Zeropoint magnitude where mag = -2.5 log( counts / exptime) + zp
#    :return: limiting magnitude
#    """
#    limit_counts = root(snr_helper, sky, args = [Nsigma_limit, readnoise, gain, sky])
#    return mag[0]

def deg2HMS(ra='', dec='', round=False):
      import string
      RA, DEC= '', ''
      if dec:
          if string.count(str(dec),':')==2:
              dec00=string.split(dec,':')
              dec0,dec1,dec2=float(dec00[0]),float(dec00[1]),float(dec00[2])
              if '-' in str(dec0):       DEC=(-1)*((dec2/60.+dec1)/60.+((-1)*dec0))
              else:                      DEC=(dec2/60.+dec1)/60.+dec0
          else:
              if str(dec)[0]=='-':      dec0=(-1)*abs(int(dec))
              else:                     dec0=abs(int(dec))
              dec1=int((abs(dec)-abs(dec0))*(60))
              dec2=((((abs(dec))-abs(dec0))*60)-abs(dec1))*60
              DEC='00'[len(str(dec0)):]+str(dec0)+':'+'00'[len(str(dec1)):]+str(dec1)+':'+'00'[len(str(int(dec2))):]+str(dec2)
      if ra:
          if string.count(str(ra),':')==2:
              ra00=string.split(ra,':')
              ra0,ra1,ra2=float(ra00[0]),float(ra00[1]),float(ra00[2])
              RA=((ra2/60.+ra1)/60.+ra0)*15.
          else:
              ra0=int(ra/15.)
              ra1=int(((ra/15.)-ra0)*(60))
              ra2=((((ra/15.)-ra0)*60)-ra1)*60
              RA='00'[len(str(ra0)):]+str(ra0)+':'+'00'[len(str(ra1)):]+str(ra1)+':'+'00'[len(str(int(ra2))):]+str(ra2)
      if ra and dec:          return RA, DEC
      else:                   return RA or DEC

def onkeypress(event):
    import matplotlib.pyplot as plt
    from numpy import polyfit,polyval,argmin,sqrt,mean,array,std,median
    global idd,_col,_dmag,testo,lines,sss,f,fixcol,aa,bb,sigmaa,sigmab
    xdata,ydata = event.xdata,event.ydata
    dist = sqrt((xdata-_col)**2+(ydata-_dmag)**2)
    ii = argmin(dist)
    if event.key == 'd' :
        __col,__dmag = _col.tolist(),_dmag.tolist()
        plt.plot(_col[ii],_dmag[ii],'xk',ms=25)
        del __col[ii],__dmag[ii]
        _col,_dmag = array(__col),array(__dmag)

    idd = range(len(_col))
    _fixcol=fixcol
    if len(_col[idd])==1:  _fixcol=0.0
    else:   _fixcol=fixcol

    if _fixcol=='':
        pol = polyfit(_col,_dmag,1,full=True)  ###
        aa = pol[0][1]
        bb = pol[0][0]
        if len(_col[idd])>2:
            sigmae = sqrt(pol[1][0]/(len(idd)  -2))
            sigmaa = sigmae*sqrt(1./len(idd)+(mean(_col[idd])**2)/sum((_col[idd]-\
                                                                           mean(_col[idd]))**2))
            sigmab = sigmae*sqrt(1/sum((_col[idd]-mean(_col[idd]))**2))
        else:
            sigmaa=0.0
            sigmab=0.0
    else:
#        aa=mean(array(_dmag[idd])-array(_col[idd])*float(_fixcol))
        aa=median(array(_dmag[idd])-array(_col[idd])*float(_fixcol))
        bb=_fixcol
        sigmaa=std(abs(aa-(array(_dmag[idd])-array(_col[idd])*float(_fixcol))))
        sigmab=0.0

    xx = [min(_col)-.1,max(_col)+.1]
    yy = polyval([bb,aa],xx)                ###
    lines.pop(0).remove()
    lines = plt.plot(xx,yy,'r-')
    plt.ylim(min(_dmag)-.2,max(_dmag)+.2)
    plt.xlabel(sss)
    plt.title(f)

    try:
        plt.setp(testo,text='%5.3f + %s* %5.3f [%4.3f  %4.3f]'%\
                     (aa,sss,bb,sigmaa,sigmab))
    except:
        plt.setp(testo,text='%5.3f + %s* %5.3f [%4.3f  %4.3f]'%\
                     (aa,sss,bb,sigmaa,sigmab))

def onclick(event):
    import matplotlib.pyplot as plt
    from numpy import polyfit,polyval,argmin,sqrt,mean,array,std,median
    global idd,_col,_dmag,testo,lines,aa,bb,sss,f,fixcol,sigmaa,sigmab
    xdata,ydata = event.xdata,event.ydata
    dist = sqrt((xdata-_col)**2+(ydata-_dmag)**2)
    ii = argmin(dist)
    if event.button == 2:
        if ii not in idd: idd.append(ii)
    if event.button == 1:  
        if ii in idd: idd.remove(ii)

    nonincl = []
    for i in range(len(_col)):
        if i not in idd: nonincl.append(i)

#    _fixcol=fixcol
    if len(_col[idd])==1:  _fixcol=0.0
    else:   _fixcol=fixcol

    if _fixcol=='':
        pol = polyfit(_col[idd],_dmag[idd],1,full=True) ###
        aa=pol[0][1]
        bb=pol[0][0]
        if len(idd)>2:
            sigmae = sqrt(pol[1][0]/(len(idd)  -2))
            sigmaa = sigmae*sqrt(1./len(idd)+(mean(_col[idd])**2)/sum((_col[idd]-\
                                                                           mean(_col[idd]))**2))
            sigmab = sigmae*sqrt(1/sum((_col[idd]-mean(_col[idd]))**2))
        else:
            sigmaa=0.0
            sigmab=0.0
    else:
#        aa=mean(_dmag[idd]-_col[idd]*float(_fixcol))
        aa=median(_dmag[idd]-_col[idd]*float(_fixcol))
        bb=_fixcol
        sigmaa=std(abs(aa-(array(_dmag[idd])-array(_col[idd])*float(_fixcol))))
        sigmab=0.0

    xx = [min(_col)-.1,max(_col)+.1]
    yy = polyval([bb,aa],xx)                ###

    plt.plot(_col,_dmag,'ok')
    plt.plot(_col[nonincl],_dmag[nonincl],'ow')
    lines.pop(0).remove()
    lines = plt.plot(xx,yy,'r-')
    plt.ylim(min(_dmag)-.2,max(_dmag)+.2)
    plt.xlabel(sss)
    plt.title(f)
    try:
        plt.setp(testo,text='%5.3f + %s* %5.3f [%4.3f  %4.3f]'%\
                     (aa,sss,bb,sigmaa,sigmab))
    except:
        plt.setp(testo,text='%5.3f + %s* %5.3f [%4.3f  %4,3f]'%\
                     (aa,sss,bb,sigmaa,sigmab))


def absphot(img,_field='',_catalogue='',_fix=True,rejection=2.,_interactive=False,_type='fit',redo=False,show=False,cutmag=-1,_calib='sloan',zcatold=False, match_by_site=False):
    filename = os.path.basename(img)
    status = lsc.myloopdef.checkstage(filename, 'zcat')
    if status < 1:
        print 'cannot run zcat stage yet:', filename
        return

    hdr = fits.getheader(img.replace('.fits', '.sn2.fits'))
    wcs = WCS(hdr)
    _cat=lsc.util.readkey3(hdr,'catalog')
    _instrume=lsc.util.readkey3(hdr,'instrume')
    _filter=lsc.util.readkey3(hdr,'filter')
    _airmass=lsc.util.readkey3(hdr,'airmass')
    _exptime=lsc.util.readkey3(hdr,'exptime')
    _date=lsc.util.readkey3(hdr,'date-obs')
    _object=lsc.util.readkey3(hdr,'object')
    _fwhm = lsc.util.readkey3(hdr,'PSF_FWHM')
    _siteid = hdr['SITEID']
    if _siteid in lsc.sites.extinction:
        kk = lsc.sites.extinction[_siteid]
    else:
        raise Exception(_siteid + ' not in lsc.sites.extinction')
    
    if _calib=='apass': _field='apass'
    if _field=='apass': _calib='apass'

    if not _catalogue:
       catalogpath, _field = lsc.util.getcatalog(filename, _field, return_field=True)
    elif _catalogue[0] in ['/', '.']:
       catalogpath = os.path.realpath(_catalogue)
    else:
       catalogpath = os.path.join(os.getenv('LCOSNDIR', lsc.util.workdirectory), 'standard', 'cat',  _catalogue)
    if not catalogpath:
        print 'could not find a catalog for', _object, _filter
        return

    catalog = os.path.basename(catalogpath)
    stdcoo = lsc.lscastrodef.readtxt(catalogpath)
    if not _field:
        fielddefs = {'landolt': {'U', 'B', 'V', 'R', 'I'},
                     'sloan': {'u', 'g', 'r', 'i', 'z'},
                     'apass': {'B', 'V', 'g', 'r', 'i'}}
        for fieldname, fieldfilts in fielddefs.items():
            if fieldfilts & set(stdcoo.colnames) == fieldfilts:
                _field = fieldname
                break
        else:
            print catalog, 'columns do not match any known field:', set(stdcoo.colnames)
            return

    if _calib == 'sloanprime' and ('fs' in _instrume or 'em' in _instrume):
        colorefisso = {'UUB':0.0,'uug':0.0,'BUB':0.0,'BBV':0.0,'VBV':0.0,'VVR':0.0,\
                      'gug':0.0,'ggr':0.0,'RVR':0.0,'RRI':0.0,'rrz':0.0,'zrz':0.0,\
                      'rgr':0.0,'rri':0.0,'iri':0.027,'iiz':0.0,'IRI':0.0,'ziz':0.0}
    elif _calib == 'sloanprime':
        colorefisso = {'UUB':0.059,'uug':0.0,'BUB':-0.095,'BBV':0.06,'VBV':0.03,'VVR':-0.059,\
                      'gug':0.13,'ggr':0.054,'RVR':-0.028,'RRI':-0.033,'rrz':0.0,'zrz':0.0,'ggi':0.0,'igi':0.0,\
                      'rgr':0.003,'rri':-0.007,'iri':0.028,'iiz':0.110,'IRI':0.013,'ziz':-0.16}
    elif _calib == 'natural':
        colorefisso = {'UUB':0.0,'uug':0.0,'BUB':0.0,'BBV':0.0,'VBV':0.0,'VVR':0.0,\
                      'gug':0.0,'ggr':0.0,'RVR':0.0,'RRI':0.0,'rrz':0.0,'zrz':0.0,\
                      'rgr':0.0,'rri':0.0,'iri':0.0,'iiz':0.0,'IRI':0.0,'ziz':0.0}
    elif 'fs' in _instrume or 'em' in _instrume:
        colorefisso = {'UUB':0.0,'uug':0.0,'BUB':0.0,'BBV':0.0,'VBV':0.0,'VVR':0.0,\
                      'gug':0.0,'ggr':0.105,'RVR':0.0,'RRI':0.0,'rrz':0.0,'zrz':0.0,\
                      'rgr':0.013,'rri':0.029,'iri':0.0874,'iiz':0.0,'IRI':0.0,'ziz':-0.15}
    # BVgri color terms from Valenti et al. 2016, MNRAS, 459, 3939
    elif 'fl' in _instrume:
        colorefisso = {'uug': 0.0, 'ggr': 0.109, 'rri': 0.027, 'iri': 0.036, 'BBV': -0.024, 'VBV': -0.014,
                       'UUB': 0.059, 'BUB': -0.095, 'VVR': -0.059, 'RVR': -0.028, 'RRI': -0.033, 'IRI': 0.013, 'ziz': -0.04}
    elif 'fa' in _instrume:
        colorefisso = {'uug': 0.0, 'ggr': 0.109, 'rri': 0.027, 'iri': 0.036, 'BBV': -0.024, 'VBV': -0.014,
                       'UUB': 0.059, 'BUB': -0.095, 'VVR': -0.059, 'RVR': -0.028, 'RRI': -0.033, 'IRI': 0.013, 'ziz': -0.04}
    elif 'ep' in _instrume:
        colorefisso = {'uug': 0.0, 'ggr': 0.0087, 'rri': 0.0166, 'iri': 0.0217, 'BBV': 0.0, 'VBV': 0.0,
                   'UUB': 0.0, 'BUB': 0.0, 'VVR': 0.0, 'RVR': 0.0, 'RRI': 0.0, 'IRI': 0.0, 'ziz': 0.0152}
    else: # don't attempt a color term if you don't know what the instrument is
        print('No color terms exist for telescope/instrument set up. No color term applied, use --unfix to calculate a color term from the field stars in the image')
        colorefisso = {'uug': 0.0, 'gug': 0.0, 'ggr': 0.0, 'rgr': 0.0, 'rri': 0.0, 'iri': 0.0, 'iiz': 0.0, 'ziz': 0.0,
                       'UUB': 0.0, 'BUB': 0.0, 'BBV': 0.0, 'VBV': 0.0, 'VVR': 0.0, 'RVR': 0.0, 'RRI': 0.0, 'IRI': 0.0}

    if _cat and not redo:
        print 'already calibrated'
    else:
     print '_' * 100
     print 'Calibrating {} to {}'.format(filename, catalog)
     lsc.mysqldef.updatevalue('photlco', 'zcat', 'X', filename)

     column=makecatalogue([img.replace('.fits', '.sn2.fits')])[_filter][img.replace('.fits', '.sn2.fits')]
     rasex=np.array(column['ra0'],float)
     decsex=np.array(column['dec0'],float)
     if _type=='fit':
        magsex=np.array(column['smagf'],float)
        magerrsex=np.array(column['smagerrf'],float)
     elif _type=='ph':
        magsex=np.array(column['magp3'],float)
        magerrsex=np.array(column['merrp3'],float)
     else:
        raise Exception(_type+' not valid (ph or fit)')
     

     if not cutmag: 
         cutmag=99

     if len(np.compress( np.array(magsex) < float(cutmag) , magsex)) < 5 : cutmag=99  # not cut if only few object
     rasex     = np.compress(np.array(magsex,float)<=cutmag,rasex)
     decsex    = np.compress(np.array(magsex,float)<=cutmag,decsex)
     magerrsex = np.compress(np.array(magsex,float)<=cutmag,magerrsex)
     magsex    = np.compress(np.array(magsex,float)<=cutmag,np.array(magsex))

     if _interactive:
        xpix, ypix = wcs.wcs_world2pix(rasex, decsex, 1)
        xy = ['{:.1f} {:.1f}'.format(x, y) for x, y in zip(xpix, ypix)]
        iraf.set(stdimage='imt1024')
        iraf.display(img + '[0]',1,fill=True,Stdout=1)
        iraf.tvmark(1,'STDIN',Stdin=list(xy),mark="circle",number='yes',label='no',radii=10,nxoffse=5,nyoffse=5,color=207,txsize=2)
        print 'yellow circles sextractor'

     stdcoo['x'], stdcoo['y'] = wcs.wcs_world2pix(stdcoo['ra'], stdcoo['dec'], 1)
     if _interactive:
           vector=['{:.1f} {:.1f}'.format(x, y) for x, y in zip(stdcoo['x'],stdcoo['y'])]
           iraf.tvmark(1,'STDIN',Stdin=vector,mark="circle",number='yes',label='no',radii=10,nxoffse=5,nyoffse=5,color=204,txsize=2)
           print 'red circles catalog'

     in_field = (stdcoo['x'] > 0) & (stdcoo['x'] < lsc.util.readkey3(hdr, 'XDIM')) & (stdcoo['y'] > 0) & (stdcoo['y'] < lsc.util.readkey3(hdr, 'YDIM'))
     if np.any(in_field):  ########   go only if standard stars are in the field  ##########
        magstd0={}
        errstd0={}
        airmass0={}
        result={}
        fileph={}
        stdcoo0 = stdcoo[in_field]
        rastd0 = stdcoo0['ra']
        decstd0 = stdcoo0['dec']
        idstd0 = stdcoo0['id']
        ###############################################################
        #               pos0 = standard                          pos1 = sextractor
        distvec, pos0, pos1 = lsc.lscastrodef.crossmatch(rastd0, decstd0, rasex, decsex, 5)
        stdcoo0 = stdcoo0[pos0]
        rastd0=rastd0[pos0]
        decstd0=decstd0[pos0]
        idstd0=idstd0[pos0]
        rasex=rasex[pos1]
        decsex=decsex[pos1]
        # after change in may 2013 mag in sn2.fits file are already at 1s
        magsex=magsex[pos1]-kk[lsc.sites.filterst1[_filter]]*float(_airmass)  #   - K x airmass
        magerrsex = magerrsex[pos1]
#################################################################################
        if _field=='landolt':
            for _filtlandolt in 'UBVRI':
                if _filtlandolt==lsc.sites.filterst1[_filter]:  airmass0[_filtlandolt]=  0 #_airmass
                else: airmass0[_filtlandolt]= 0
                magstd0[_filtlandolt]=stdcoo0[_filtlandolt]
                errstd0[_filtlandolt]=stdcoo0[_filtlandolt+'err']
            fileph['mU']=np.tile(999, len(rastd0))
            fileph['mB']=np.tile(999, len(rastd0))
            fileph['mV']=np.tile(999, len(rastd0))
            fileph['mR']=np.tile(999, len(rastd0))
            fileph['mI']=np.tile(999, len(rastd0))
            fileph['V']=magstd0['V']
            fileph['BV']=np.array(np.array(magstd0['B'],float)-np.array(magstd0['V'],float),str)
            fileph['UB']=np.array(np.array(magstd0['U'],float)-np.array(magstd0['B'],float),str)
            fileph['VR']=np.array(np.array(magstd0['V'],float)-np.array(magstd0['R'],float),str)
            fileph['RI']=np.array(np.array(magstd0['R'],float)-np.array(magstd0['I'],float),str)
        elif _field=='sloan':
            for _filtsloan in 'ugriz':
                if _filtsloan==lsc.sites.filterst1[_filter]:  airmass0[_filtsloan]= 0   # _airmass
                else: airmass0[_filtsloan]=0
                magstd0[_filtsloan]=stdcoo0[_filtsloan]
                errstd0[_filtsloan]=stdcoo0[_filtsloan+'err']
            magstd0['w'] = magstd0['r']
            errstd0['w'] = errstd0['r']
            fileph['mu']=np.tile(999, len(rastd0))
            fileph['mg']=np.tile(999, len(rastd0))
            fileph['mr']=np.tile(999, len(rastd0))
            fileph['mi']=np.tile(999, len(rastd0))
            fileph['mz']=np.tile(999, len(rastd0))
            fileph['mw'] = fileph['mr']
            fileph['r']=magstd0['r']
            fileph['gr']=np.array(np.array(magstd0['g'],float)-np.array(magstd0['r'],float),str)
            fileph['ri']=np.array(np.array(magstd0['r'],float)-np.array(magstd0['i'],float),str)
            fileph['ug']=np.array(np.array(magstd0['u'],float)-np.array(magstd0['g'],float),str)
            fileph['iz']=np.array(np.array(magstd0['i'],float)-np.array(magstd0['z'],float),str)
        elif _field=='apass':
            for _filtsloan in 'BVgri':
                if _filtsloan==lsc.sites.filterst1[_filter]:  airmass0[_filtsloan]= 0   # _airmass
                else: airmass0[_filtsloan]=0
                magstd0[_filtsloan]=stdcoo0[_filtsloan]
                errstd0[_filtsloan]=stdcoo0[_filtsloan+'err']
            magstd0['w'] = magstd0['r']
            errstd0['w'] = errstd0['r']
            fileph['mB']=np.tile(999, len(rastd0))
            fileph['mV']=np.tile(999, len(rastd0))
            fileph['mg']=np.tile(999, len(rastd0))
            fileph['mr']=np.tile(999, len(rastd0))
            fileph['mi']=np.tile(999, len(rastd0))
            fileph['mw'] = fileph['mr']
            fileph['V']=magstd0['V']
            fileph['BV']=np.array(np.array(magstd0['B'],float)-np.array(magstd0['V'],float),str)
            fileph['gr']=np.array(np.array(magstd0['g'],float)-np.array(magstd0['r'],float),str)
            fileph['ri']=np.array(np.array(magstd0['r'],float)-np.array(magstd0['i'],float),str)
            fileph['Vg']=np.array(np.array(magstd0['V'],float)-np.array(magstd0['g'],float),str)
########################################################################################
        zero=[]
        zeroerr = []
        magcor=[]
        fil = open(img.replace('.fits', '.ph'), 'w')
        fil.write(str(_instrume)+' '+str(_date)+'\n')
        fil.write('*** '+_object+' '+str(len(magsex))+'\n')
        if _field=='landolt':
            fil.write('%6.6s\t%6.6s\t%6.6s\t%6.6s\t%6.6s\n' % (str(1),str(1),str(1),str(1),str(1)))  # exptime
            fil.write('%6.6s\t%6.6s\t%6.6s\t%6.6s\t%6.6s\n' % (str(airmass0['U']),str(airmass0['B']),str(airmass0['V']),str(airmass0['R']),str(airmass0['I'])))
        elif _field=='sloan':
            fil.write('%6.6s\t%6.6s\t%6.6s\t%6.6s\t%6.6s\n' % (str(1),str(1),str(1),str(1),str(1)))  # exptime
            fil.write('%6.6s\t%6.6s\t%6.6s\t%6.6s\t%6.6s\n' % (str(airmass0['u']),str(airmass0['g']),str(airmass0['r']),str(airmass0['i']),str(airmass0['z'])))
        elif _field=='apass':
            fil.write('%6.6s\t%6.6s\t%6.6s\t%6.6s\t%6.6s\n' % (str(1),str(1),str(1),str(1),str(1)))  # exptime
            fil.write('%6.6s\t%6.6s\t%6.6s\t%6.6s\t%6.6s\n' % (str(airmass0['B']),str(airmass0['V']),str(airmass0['g']),str(airmass0['r']),str(airmass0['i'])))
        for i in range(0,len(magsex)): 
            fileph['m'+lsc.sites.filterst1[_filter]][i]=magsex[i]    #  instrumental mangitude of std in pos0[i]
            if _field=='landolt':
                stringastandard='%12.12s\t%7.7s\t%7.7s\t%7.7s\t%7.7s\t%7.7s' % (idstd0[i],fileph['V'][i],fileph['BV'][i],fileph['UB'][i],\
                                                                                fileph['VR'][i],fileph['RI'][i])
                fil.write('%7.7s\t%7.7s\t%7.7s\t%7.7s\t%7.7s\t%60.60s\n' \
                              % (str(fileph['mU'][i]),str(fileph['mB'][i]),str(fileph['mV'][i]),str(fileph['mR'][i]),str(fileph['mI'][i]),str(stringastandard)))
            elif _field=='sloan':
                stringastandard='%12.12s\t%7.7s\t%7.7s\t%7.7s\t%7.7s\t%7.7s' % (idstd0[i],fileph['r'][i],fileph['gr'][i],fileph['ug'][i],\
                                                                                fileph['ri'][i],fileph['iz'][i])
                fil.write('%7.7s\t%7.7s\t%7.7s\t%7.7s\t%7.7s\t%60.60s\n' \
                              % (str(fileph['mu'][i]),str(fileph['mg'][i]),str(fileph['mr'][i]),str(fileph['mi'][i]),str(fileph['mz'][i]),str(stringastandard)))
            elif _field=='apass':
                stringastandard='%12.12s\t%7.7s\t%7.7s\t%7.7s\t%7.7s\t%7.7s' % (idstd0[i],fileph['V'][i],fileph['BV'][i],fileph['Vg'][i],\
                                                                                fileph['gr'][i],fileph['ri'][i])
                fil.write('%7.7s\t%7.7s\t%7.7s\t%7.7s\t%7.7s\t%60.60s\n' \
                              % (str(fileph['mB'][i]),str(fileph['mV'][i]),str(fileph['mg'][i]),str(fileph['mr'][i]),str(fileph['mi'][i]),str(stringastandard)))
            zero.append(float(magstd0[lsc.sites.filterst1[_filter]][i])-float(magsex[i]))
            zeroerr.append((float(errstd0[lsc.sites.filterst1[_filter]][i])**2 + magerrsex[i]**2)**0.5)
            magcor.append(magsex[i])
        fil.close()
        magstdn=lsc.lscabsphotdef.transform2natural(_instrume,magstd0,colorefisso,_field)

        magsex1=magsex+kk[lsc.sites.filterst1[_filter]]*float(_airmass)  #   add again extinction for natural zero point comparison

        media,mediaerr,mag2,data2=lsc.lscabsphotdef.zeropoint2(np.array(magstdn[lsc.sites.filterst1[_filter]],float),np.array(magsex1,float),10,2,show)

        if media!=9999: 
              _limmag = limmag(img, media, 3, _fwhm)     #   compute limiting magnitude at 3 sigma
              lsc.mysqldef.updatevalue('photlco', ['limmag', 'zn', 'dzn', 'znnum'], [_limmag, media, mediaerr, len(data2)], filename)

        filters_observed = get_other_filters(filename, match_by_site)
        filters_in_catalog = set(magstd0.keys())
        colors = lsc.sites.chosecolor(filters_observed & filters_in_catalog, False)
        colorvec=colors[lsc.sites.filterst1[_filter]]
        zero = np.array(zero)
        zeroerr = np.array(zeroerr)
        print 'attempting these colors:', colorvec
        if not colorvec:
            colorvec.append(2*lsc.sites.filterst1[_filter])
        if not zcatold and show and not _interactive:
            fig, axarr = plt.subplots(ncols=len(colorvec), figsize=(8*len(colorvec), 6), squeeze=False)
        for i, col in enumerate(colorvec):
            col0=magstd0[col[0]] 
            col1=magstd0[col[1]]
            colstd0=np.array(col0,float)-np.array(col1,float)
            colerr0 = errstd0[col[0]]
            colerr1 = errstd0[col[1]]
            colerrstd0 = (np.array(colerr0, float)**2 + np.array(colerr1, float)**2)**0.5

#            colore=[]
#            for i in range(0,len(pos1)):   colore.append(colstd0[i])
            # cut stars with crazy magnitude and color
#            colore1=np.compress(abs(np.array(zero))<50,np.array(colore))
#            zero1=np.compress(abs(np.array(zero))<50,np.array(zero))
            if _filter in ['up', 'zs']: maxcolor = 10
            else:                       maxcolor = 2
#            zero2=np.compress(abs(np.array(colore1)) < maxcolor,np.array(zero1))
#            colore2=np.compress(abs(np.array(colore1)) < maxcolor,np.array(colore1))

            good = (abs(zero) < 50) & (abs(colstd0) < maxcolor) & (zeroerr != 0) & (colerrstd0 != 0)
            zero2 = zero[good]
            colore2 = colstd0[good]
            zeroerr2 = zeroerr[good]
            coloreerr2 = colerrstd0[good]

            if _fix and lsc.sites.filterst1[_filter]+col in colorefisso:
                fisso = colorefisso[lsc.sites.filterst1[_filter]+col]
            elif col == 2*lsc.sites.filterst1[_filter]:
                fisso = 0.
            else:
                fisso = None

            if len(colore2)==0:
                print 'no calibration:', lsc.sites.filterst1[_filter], col, _field
                continue
#                b,a,sa,sb=9999,9999,0,0
            else:
                if zcatold:
                    if _interactive:    a,sa,b,sb=fitcol(colore2,zero2,_filter,col,fisso)
                    else:               a,sa,b,sb=fitcol2(colore2,zero2,_filter,col,fisso,show,rejection)
                else:
                    if show and not _interactive:
                        plt.axes(axarr[0, i])
                    a, sa, b, sb = fitcol3(colore2, zero2, coloreerr2, zeroerr2, fisso, _filter, ' - '.join(col), show, _interactive, rejection)
            result[lsc.sites.filterst1[_filter]+col]=[a,sa,b,sb]
        if result:
            lsc.util.updateheader(img.replace('.fits', '.sn2.fits'), 0, {'CATALOG': (catalog, 'catalogue source')})
            for ll in result:
                for kk in range(0,len(result[ll])):
                                    if not np.isfinite(result[ll][kk]): result[ll][kk]=0.0 
                valore='%3.3s %6.6s %6.6s  %6.6s  %6.6s' %  (str(ll),str(result[ll][0]),str(result[ll][2]),str(result[ll][1]),str(result[ll][3]))
                lsc.util.updateheader(img.replace('.fits', '.sn2.fits'), 0, {'zp'+ll:(str(valore),'a b sa sb in y=a+bx')})
                print '### added to header:', valore
                if ll[0]==ll[2]: num=2
                elif ll[0]==ll[1]: num=1
                else: raise Exception('somthing wrong with color '+ll)
                columns = ['zcol'+str(num), 'z'+str(num), 'c'+str(num), 'dz'+str(num), 'dc'+str(num), 'zcat']
                values = [ll[1:], result[ll][0], result[ll][2], result[ll][1], result[ll][3], 'X' if result[ll][0] == 9999 else catalog]
                lsc.mysqldef.updatevalue('photlco', columns, values, filename)
                
#################################################################
#################### new zero point calculation #################
def fitcol3(colors, deltas, dcolors=None, ddeltas=None, fixedC=None, filt='', col='Color', show=False, interactive=False, clipsig=2, extra=False):
    if interactive:
        global keep, Z, dZ, C, dC
        plt.cla()
    if fixedC is None: # color term is not fixed
        # fit Theil-Sen line and find outliers
        C, Z, _, _ = stats.theilslopes(deltas, colors) # delta = calibrated mag - instrumental mag
        zeros = deltas - C*colors # zeros are the "zero points" for individual stars
        dzeros = (ddeltas**2 + (C*dcolors)**2)**0.5
        resids = zeros - Z
        keep = abs(resids) <= clipsig*dzeros
        if sum(keep) <= 5: # if there aren't very many points, use fixed color term
            if filt=='g': fixedC = 0.1
            else:         fixedC = 0
            print 'Not enough points (after rejection). Defaulting to C = {:.2f}.'.format(fixedC)
    if fixedC is not None: # color term is fixed
        C = fixedC
        zeros = deltas - C*colors
        dzeros = (ddeltas**2 + (C*dcolors)**2)**0.5
        Z = np.median(zeros)
        resids = zeros - Z
        keep = abs(resids) <= clipsig*dzeros
    Z, dZ, C, dC = calcZC(colors, deltas, dcolors, ddeltas, fixedC, filt, col, (show or interactive), guess=[Z, C])
    if interactive:
        def onpick(event):
            global keep, Z, dZ, C, dC
            i = event.ind[0] # find closest point
            keep[i] = not keep[i] # toggle rejection
            print
            Z, dZ, C, dC = calcZC(colors, deltas, dcolors, ddeltas, fixedC, filt, col, show=True, guess=[Z, C])
        cid = plt.gcf().canvas.mpl_connect('pick_event', onpick)
        raw_input('Press enter to continue.')
        plt.gcf().canvas.mpl_disconnect(cid)
    elif fixedC is None and C > 0.3: # if the color term is too crazy, use fixed color term
        if filt=='g': fixedC = 0.1
        else:         fixedC = 0
        print 'C = {:.2f} is too crazy. Redoing with C = {:.2f}.'.format(C, fixedC)
        C = fixedC
        zeros = deltas - C*colors
        dzeros = (ddeltas**2 + (C*dcolors)**2)**0.5
        Z = np.median(zeros)
        resids = zeros - Z
        keep = abs(resids) <= clipsig*dzeros
        Z, dZ, C, dC = calcZC(colors, deltas, dcolors, ddeltas, fixedC, filt, col, show, guess=[Z, C])
    if extra: return Z, dZ, C, dC, keep
    else: return Z, dZ, C, dC

def calcZC(colors, deltas, dcolors=None, ddeltas=None, #keep=None,
           fixedC=None, filt='', col='Color', show=False, guess=[23., 0.03], extra=False):
    if fixedC is None:
        def f(B, x): return B[0] + B[1]*x
        linear = odr.Model(f)
        mydata = odr.Data(colors[keep], deltas[keep], wd=dcolors[keep]**-2, we=ddeltas[keep]**-2)
        myodr = odr.ODR(mydata, linear, beta0=guess) # start from typical values
        myoutput = myodr.run()
        Z, C = myoutput.beta
        dZ, dC = myoutput.sd_beta
        x_reg = myoutput.xplus
        y_reg = myoutput.y
    elif np.any(keep):
        Z, sum_of_weights = np.average(deltas[keep] - fixedC * colors[keep], weights=1/(ddeltas[keep]**2 + dcolors[keep]**2), returned=True)
        dZ = sum_of_weights**-0.5
        C, dC = fixedC, 0
    else:
        Z, C = guess
        dZ, dC = 0, 0
    print 'zero point = {:5.2f} +/- {:4.2f}'.format(Z, dZ)
    print 'color term = {:5.2f} +/- {:4.2f}'.format(C, dC)
    if show:
        if not plt.gca().get_autoscale_on():
            lims = plt.axis()
        else:
            lims = [None, None, None, None]
        plt.cla()
        plt.scatter(colors, deltas, marker='.', picker=5)
        plt.errorbar(colors[keep], deltas[keep], xerr=dcolors[keep], yerr=ddeltas[keep], color='g', marker='o', linestyle='none')
        plt.errorbar(colors[~keep], deltas[~keep], xerr=dcolors[~keep], yerr=ddeltas[~keep], color='r', marker='o', linestyle='none')
        plt.axis(lims)
        plt.autoscale(False)
        xx = np.array(plt.axis()[0:2])
        yy = Z + C*xx
        plt.plot(xx, yy, '--')
        plt.xlabel(col)
        plt.ylabel('Calibrated Mag - Instrumental Mag')
        plt.title(filt)
        plt.pause(0.1)
    if fixedC is None and extra: return Z, dZ, C, dC, x_reg, y_reg
    else: return Z, dZ, C, dC
#################################################################
#################################################################
def fitcol(col,dmag,band,color,fissa=''):
    import matplotlib.pyplot as plt 
    from numpy import polyfit,polyval,argmin,sqrt,mean,array,std,median
    global idd,_col,_dmag,testo,lines,pol,sss,f,fixcol,sigmaa,sigmab,aa,bb
    plt.ion()
    fig = plt.figure()
    _dmag = dmag[:]
    _col  = col[:]
    sss=band
    f=color
    fixcol=fissa
    _col = array(_col)
    _dmag = array(_dmag)
    idd = range(len(_col))
    plt.plot(_col,_dmag,'ok')

    _fixcol=fixcol
    if len(_col[idd])==1:  _fixcol=0.0
    else:   _fixcol=fixcol

    if _fixcol=='':
        pol = polyfit(_col[idd],_dmag[idd],1,full=True) ###
        aa=pol[0][1]
        bb=pol[0][0]

        if len(idd)>2:
            sigmae = sqrt(pol[1][0]/(len(idd)  -2))
            sigmaa = sigmae*sqrt(1./len(idd)+(mean(_col[idd])**2)/sum((_col[idd]-\
                                                                           mean(_col[idd]))**2))
            sigmab = sigmae*sqrt(1/sum((_col[idd]-mean(_col[idd]))**2))
        else:
            sigmaa=0.0
            sigmab=0.0
    else:
#            aa=mean(array(_dmag)[idd]-array(_col)[idd]*fixcol)
            aa=median(array(_dmag)[idd]-array(_col)[idd]*fixcol)
            bb=fixcol
            sigmaa=std(abs(aa-(array(_dmag)-array(_col)*float(_fixcol))))
            sigmab=0.0

    xx = [min(_col)-.1,max(_col)+.1]
    yy = polyval([bb,aa],xx)                ###
    lines = plt.plot(xx,yy,'r-')
    plt.ylim(min(_dmag)-.2,max(_dmag)+.2)
    plt.xlim(min(xx),max(xx))
    plt.xlabel(sss)
    plt.title(f)
    try:
        testo = plt.figtext(.2,.85,'%5.3f + %s* %5.3f [%4.3f  %4.3f]'%\
                             (aa,sss,bb,sigmaa,sigmab))
    except:
        testo = plt.figtext(.2,.85,'%5.3f + %s* %5.3f [%4.3f  %4.3f]'%\
                             (aa,sss,bb,sigmaa,sigmab))

    kid = fig.canvas.mpl_connect('key_press_event',onkeypress)
    cid = fig.canvas.mpl_connect('button_press_event',onclick)
    plt.draw()
    raw_input('left-click mark bad, right-click unmark, <d> remove. Return to exit ...')
    plt.close()
    print '####'
    print sigmaa,sigmab, aa,bb
    return aa,sigmaa,bb,sigmab

#################################################################

def fitcol2(_col,_dmag,band,col,fixcol='',show=False,rejection=2):
    from numpy import polyfit,polyval,argmin,sqrt,mean,array,std,compress
    sss=band
    f=col
    if len(_col)>1:
        if fixcol:
            slope=fixcol
            mean0,sig0,yy0,xx0=lsc.lscabsphotdef.meanclip2(_col,_dmag,fixcol, clipsig=rejection, maxiter=5, converge_num=.99, verbose=0)
            xx = [min(_col)-.1,max(_col)+.1]
            yy = polyval([fixcol,mean0],_col)                ###
            try:      sigmae = sqrt(sig0/(len(xx0)  -2))
            except:   sigmae=0
            sigmaa = sigmae*sqrt(1./len(xx0)+(mean(xx0)**2)/sum((xx0-mean(xx0))**2))
            sigmab=0.0
        else:
            mean0,sig0,slope,yy0,xx0=lsc.lscabsphotdef.meanclip3(_col,_dmag,fixcol, clipsig=rejection, maxiter=5, converge_num=.99, verbose=0)
            xx = [min(_col)-.1,max(_col)+.1]
            yy = polyval([slope,mean0],_col)                ###
            try:      sigmae = sqrt(sig0/(len(xx0)  -2))
            except:   sigmae=0
            sigmaa = sigmae*sqrt(1./len(xx0)+(mean(xx0)**2)/sum((xx0-mean(xx0))**2))
            sigmab = sigmae*sqrt(1/sum((xx0-mean(xx0))**2))
        if show:
            import time
            import matplotlib.pyplot as plt
            plt.ion()
            plt.clf()
            plt.plot(_col,_dmag,'ob')
            plt.plot(xx0,yy0,'xr')
            plt.plot(_col,yy,'-g')
            plt.ylabel('zeropoint')
            plt.xlabel(f)
            plt.title(sss)
            plt.draw()
            time.sleep(1)
    try:
        print '###', mean0, sigmaa, slope, sigmab
    except:
        print '\n### zeropoint not computed'
        mean0,sigmaa,slope,sigmab=9999,9999,9999,9999
    return mean0,sigmaa,slope,sigmab

def meanclip2(xx,yy,slope, clipsig=3.0, maxiter=5, converge_num=0.1, verbose=0):
    from numpy import array
    import numpy
    xx=array(xx)
    yy=array(yy)
    xx0=array(xx[:])
    yy0=array(yy[:])
    ct=len(yy)
    slope=float(slope)
    iter = 0; c1 = 1.0 ; c2 = 0.0
    while (c1 >= c2) and (iter < maxiter):
        lastct = ct
        sig=numpy.std(yy0-xx0*slope)
#        mean=numpy.mean(array(yy0)-array(xx0)*slope)
        mean=numpy.median(array(yy0)-array(xx0)*slope)
        wsm = numpy.where( abs(yy0-xx0*slope) < mean+clipsig*sig )
        ct = len(wsm[0])
        if ct > 0:
            xx0=xx0[wsm]
            yy0=yy0[wsm]
        c1 = abs(ct - lastct)
        c2 = converge_num * lastct
        iter += 1
# End of while loop
#    mean=numpy.mean(array(yy0)-array(xx0)*slope)
    mean=numpy.median(array(yy0)-array(xx0)*slope)
    sig=numpy.std(array(yy0)-array(xx0)*float(slope))
    if verbose: pass
    return mean, sig,yy0,xx0

def meanclip3(xx,yy,slope, clipsig=3.0, maxiter=5, converge_num=0.1, verbose=0):
    from numpy import array, polyfit
    import numpy
    xx=array(xx)
    yy=array(yy)
    xx0=array(xx[:])
    yy0=array(yy[:])
    ct=len(yy)
    iter = 0; c1 = 1.0 ; c2 = 0.0
    while (c1 >= c2) and (iter < maxiter):
        lastct = ct
        pol = polyfit(xx0,yy0,1,full=True) ###
        mean0=pol[0][1]
        slope=pol[0][0]
        sig=numpy.std(yy0-mean0-slope*xx0)
        wsm = numpy.where( abs(yy0-xx0*slope) < mean0+clipsig*sig )
        ct = len(wsm[0])
        if ct > 0:
            xx0=xx0[wsm]
            yy0=yy0[wsm]
        c1 = abs(ct - lastct)
        c2 = converge_num * lastct
        iter += 1
# End of while loop
    pol = polyfit(xx0,yy0,1,full=True) ###
    mean0=pol[0][1]
    slope=pol[0][0]
    sig=numpy.std(yy0-mean0-slope*xx0)
    if verbose: pass
    return mean0, sig,slope,yy0,xx0

########################################################################

def makecatalogue(imglist):
    from astropy.io import fits
    from numpy import array, zeros
    dicti={}
    for img in imglist:
        t = fits.open(img)
        tbdata = t[1].data
        hdr1=t[0].header
        _filter=lsc.util.readkey3(hdr1,'filter')
        if _filter not in dicti: dicti[_filter]={}
        if img not in dicti[_filter]: dicti[_filter][img]={}
        for jj in hdr1:
            if jj[0:2]=='ZP':
                dicti[_filter][img][jj]=lsc.util.readkey3(hdr1,jj)

#######################
#       early data may have JD instead of mjd in the fits table
#
        if 'MJD' in hdr1.keys():
              dicti[_filter][img]['mjd']=lsc.util.readkey3(hdr1,'MJD')
        else:
              dicti[_filter][img]['mjd']=lsc.util.readkey3(hdr1,'JD')
        dicti[_filter][img]['JD']=dicti[_filter][img]['mjd']
#######################

        dicti[_filter][img]['exptime']=lsc.util.readkey3(hdr1,'exptime')
        dicti[_filter][img]['airmass']=lsc.util.readkey3(hdr1,'airmass')
        dicti[_filter][img]['telescope']=lsc.util.readkey3(hdr1,'telescop')
        dicti[_filter][img]['siteid']=hdr1['SITEID']
        
        for col in tbdata.columns.names:
            dicti[_filter][img][col]=tbdata.field(col)
        if 'ra0' not in tbdata.columns.names:
            dicti[_filter][img]['ra0']=array(zeros(len(dicti[_filter][img]['ra'])),float)
            dicti[_filter][img]['dec0']=array(zeros(len(dicti[_filter][img]['ra'])),float)
            for i in range(0,len(dicti[_filter][img]['ra'])):
#                dicti[_filter][img]['ra0'][i]=float(iraf.real(dicti[_filter][img]['ra'][i]))*15
#                dicti[_filter][img]['dec0'][i]=float(iraf.real(dicti[_filter][img]['dec'][i]))
                dicti[_filter][img]['ra0'][i],dicti[_filter][img]['dec0'][i]=lsc.lscabsphotdef.deg2HMS(dicti[_filter][img]['ra'][i],dicti[_filter][img]['dec'][i])
    return dicti

######################################################################################################
def finalmag(Z1,Z2,C1,C2,m1,m2):
    color=(Z1-Z2+m1-m2)/(1-(C1-C2))
    print 'color ',color
    print Z1,C1,m1
    print Z2,C2,m2
    M1=Z1+C1*color+m1
    M2=Z2+C2*color+m2
    return M1,M2

def erroremag(z0,z1,m0,m1,c0,c1,position): #  z=zeropoint,m=magnitude,colorterm  
    if position==0:   #    error for first band in the color: (e.g.  V in VR) 
        dm0=1+(c0/(1-(c0-c1)))
        dz0=1+(c0/(1-(c0-c1)))
        dm1=(-1)*(c0/(1-(c0-c1)))
        dz1=(-1)*(c0/(1-(c0-c1)))
        dc0=(z0+m0-z1-m1)*(1+c1)*(1/(1-(c0-c1))**2)
        dc1=(-1)*(z0+m0-z1-m1)*(c0)*(1/(1-(c0-c1))**2)
    elif position==1:   #    error for second band in the color: (e.g.  R in VR) 
        dm0=1-(c1/(1-(c0-c1)))
        dz0=1-(c1/(1-(c0-c1)))
        dm1=(-1)*(c1/(1-(c0-c1)))
        dz1=(-1)*(c1/(1-(c0-c1)))
        dc0=(z0+m0-z1-m1)*(1-c0)*(1/(1-(c0-c1))**2)
        dc1=(z0+m0-z1-m1)*(c1)*(1/(1-(c0-c1))**2) 
    else:
        # added to make the pipeline working, but error not good
        dm0=1
        dz0=0
        dm1=1
        dz1=0
        dc0=0
        dc1=0
    return dc0,dc1,dz0,dz1,dm0,dm1

#################################################################

def zeropoint(data,mag,maxiter=10,nn=2,show=False):
    import numpy as np
    z0=np.mean(data)
    std0=np.std(data)
    data1=data[:]
    mag1=mag[:]
    data2=np.compress((data < (z0+std0)) & (data>(z0-std0)),data)
    mag2=np.compress((data < (z0+std0)) & (data>(z0-std0)),mag)
    z2=np.mean(data2)
    std2=np.std(data2)
    iter=0; 
    if show:  
        import matplotlib.pyplot as pl
        pl.ion()

    while iter < maxiter and len(data2)>5:
        z1=np.mean(data1)
        std1=np.std(data1)
        z2=np.mean(data2)
        std2=np.std(data2)
        if show:
            print 'rejected '+str(len(data1)-len(data2))+' point'
            print z1,std1,len(data1)
            print z2,std2,len(data2)

        if np.abs(z2-z1)<std2/np.sqrt(len(data2)):
            if show:
                print 'zero points are within std2 '
                pl.clf()
                pl.plot(mag1,data1,'or')
                pl.plot(mag2,data2,'xg')
            break
        else:
            data1=np.compress((data < (z1+nn*std1)) & (data>(z1-nn*std1)),data)
            data2=np.compress((data < (z2+nn*std2)) & (data>(z2-nn*std2)),data)
            mag1=np.compress((data < (z1+nn*std1)) & (data>(z1-nn*std1)),mag)
            mag2=np.compress((data < (z2+nn*std2)) & (data>(z2-nn*std2)),mag)
            z1=np.mean(data1)
            std1=np.std(data1)
            z2=np.mean(data2)
            std2=np.std(data2)
        iter += 1
        if show:
            print 'iteration '+str(iter)
            print z1,std1,len(data1)
            print z2,std2,len(data2)
            pl.clf()
            pl.plot(mag,data,'or')
            pl.plot(mag2,data2,'*g')
    return z2,std2,mag2,data2

#############################################

def zeropoint2(xx,mag,maxiter=10,nn=2,show=False,_cutmag=99):
   if len(xx):
      import numpy as np
      if float(_cutmag)!=99:
         print 'cut mag '+str(_cutmag)
         xx=np.compress(mag<_cutmag,xx)
         mag=np.compress(mag<_cutmag,mag)
      data=np.array(xx-mag)
      z0=np.median(data)
      std0=np.std(data)
      data1=data[:]
      mag1=mag[:]
      data2=np.compress((data < (z0+nn*std0)) & (data>(z0-nn*std0)),data)
      mag2=np.compress((data < (z0+nn*std0)) & (data>(z0-nn*std0)),mag)
      z2, std2 = 9999, 9999
      iter=0; 
      if show:  
            print len(data2)
            import matplotlib.pyplot as pl
            pl.ion()
            pl.clf()
            pl.plot(mag,data,'or')
            pl.plot(mag2,data2,'*g')
      while iter < maxiter and len(data2)>5:
          z1=np.mean(data1)
          std1=np.std(data1)
          z2=np.mean(data2)
          std2=np.std(data2)
          if show:
              print 'rejected '+str(len(data1)-len(data2))+' point'
              print z1,std1,len(data1)
              print z2,std2,len(data2)
          if np.abs(z2-z1)<std2/np.sqrt(len(data2)):
              if show:
                  print 'zero points are within std2 '
                  pl.clf()
                  pl.plot(mag1,data1,'or')
                  pl.plot(mag2,data2,'xg')
              break
          else:
              data1=np.compress((data < (z1+nn*std1)) & (data>(z1-nn*std1)),data)
              data2=np.compress((data < (z2+nn*std2)) & (data>(z2-nn*std2)),data)
              mag1=np.compress((data < (z1+nn*std1)) & (data>(z1-nn*std1)),mag)
              mag2=np.compress((data < (z2+nn*std2)) & (data>(z2-nn*std2)),mag)
              z1=np.mean(data1)
              std1=np.std(data1)
              z2=np.mean(data2)
              std2=np.std(data2)
          iter += 1
          if show:
              print 'iteration '+str(iter)
              print z1,std1,len(data1)
              print z2,std2,len(data2)
              pl.clf()
              pl.plot(mag,data,'or')
              pl.plot(mag2,data2,'*g')
      if np.isnan(z2): z2,std2= 9999, 9999
   else:
      z2,std2,mag2,data2=9999,9999,9999,9999
   return z2,std2,mag2,data2

########################################################################

def transform2natural(_instrument,_catalogue,colorefisso,_inputsystem='sloan'):
   import numpy as np
   _catalogue2={}
   for i in _catalogue.keys():
      _catalogue2[i]=np.array(_catalogue[i][:],float)
   if _inputsystem in ['sloan','sloanprime']:
      col={}
      col['ug']=[(_catalogue2['u'][i]-_catalogue2['g'][i]) if (_catalogue2['u'][i]<99 and _catalogue2['g'][i]<99) else  (_catalogue2['u'][i]-_catalogue2['u'][i]) for i in range(0,len(_catalogue2['u']))]
      col['gr']=[(_catalogue2['g'][i]-_catalogue2['r'][i]) if (_catalogue2['g'][i]<99 and _catalogue2['r'][i]<99) else  (_catalogue2['g'][i]-_catalogue2['g'][i]) for i in range(0,len(_catalogue2['g']))]
      col['ri']=[(_catalogue2['r'][i]-_catalogue2['i'][i]) if (_catalogue2['r'][i]<99 and _catalogue2['i'][i]<99) else  (_catalogue2['r'][i]-_catalogue2['r'][i]) for i in range(0,len(_catalogue2['r']))]
      col['iz']=[(_catalogue2['i'][i]-_catalogue2['z'][i]) if (_catalogue2['i'][i]<99 and _catalogue2['z'][i]<99) else  (_catalogue2['i'][i]-_catalogue2['i'][i]) for i in range(0,len(_catalogue2['i']))]
      _catalogue2['u']=_catalogue2['u']-colorefisso['uug']*np.array(col['ug'])#(_catalogue['u']-_catalogue['g'])
      _catalogue2['g']=_catalogue2['g']-colorefisso['ggr']*np.array(col['gr'])#(_catalogue['g']-_catalogue['r'])
      _catalogue2['r']=_catalogue2['r']-colorefisso['rri']*np.array(col['ri'])#(_catalogue['r']-_catalogue['i'])
      _catalogue2['i']=_catalogue2['i']-colorefisso['iri']*np.array(col['ri'])#(_catalogue['r']-_catalogue['i'])
      _catalogue2['z']=_catalogue2['z']-colorefisso['ziz']*np.array(col['iz'])#(_catalogue['i']-_catalogue['z'])
      print 'transform '+str(_inputsystem)+' to natural system'
      print 'un = u - '+str(colorefisso['uug'])+' * (u-g)'
      print 'gn = g - '+str(colorefisso['ggr'])+' * (g-r)'
      print 'rn = r - '+str(colorefisso['rri'])+' * (r-i)'
      print 'in = i - '+str(colorefisso['iri'])+' * (r-i)'
      print 'zn = z - '+str(colorefisso['ziz'])+' * (i-z)'
   elif _inputsystem in ['landolt']:
      col={}
      col['UB']=[(_catalogue2['U'][i]-_catalogue2['B'][i]) if (_catalogue2['U'][i]<99 and _catalogue2['B'][i]<99) else  (_catalogue2['B'][i]-_catalogue2['B'][i]) for i in range(0,len(_catalogue2['U']))]
      col['BV']=[(_catalogue2['B'][i]-_catalogue2['V'][i]) if (_catalogue2['B'][i]<99 and _catalogue2['V'][i]<99) else  (_catalogue2['B'][i]-_catalogue2['B'][i]) for i in range(0,len(_catalogue2['B']))]
      col['VR']=[(_catalogue2['V'][i]-_catalogue2['R'][i]) if (_catalogue2['V'][i]<99 and _catalogue2['R'][i]<99) else  (_catalogue2['V'][i]-_catalogue2['V'][i]) for i in range(0,len(_catalogue2['V']))]
      col['RI']=[(_catalogue2['R'][i]-_catalogue2['I'][i]) if (_catalogue2['R'][i]<99 and _catalogue2['I'][i]<99) else  (_catalogue2['R'][i]-_catalogue2['R'][i]) for i in range(0,len(_catalogue2['R']))]
      _catalogue2['U']=_catalogue2['U']-colorefisso['UUB']*np.array(col['UB'])#(_catalogue['U']-_catalogue['B'])
      _catalogue2['B']=_catalogue2['B']-colorefisso['BBV']*np.array(col['BV'])#(_catalogue['B']-_catalogue['V'])
      _catalogue2['V']=_catalogue2['V']-colorefisso['VVR']*np.array(col['VR'])#(_catalogue['V']-_catalogue['R'])
      _catalogue2['R']=_catalogue2['R']-colorefisso['RVR']*np.array(col['VR'])#(_catalogue['V']-_catalogue['R'])
      _catalogue2['I']=_catalogue2['I']-colorefisso['IRI']*np.array(col['RI'])#(_catalogue['R']-_catalogue['I'])
      print 'transform '+str(_inputsystem)+' to natural system'
      print "Un = U - "+str(colorefisso['UUB'])+" * (U-B)"
      print "Bn = B - "+str(colorefisso['BBV'])+" * (B-V)"
      print "Vn = V - "+str(colorefisso['VVR'])+" * (V-R)"
      print "Rn = R - "+str(colorefisso['RVR'])+" * (V-R)"
      print "In = I - "+str(colorefisso['IRI'])+" * (R-I)"
   elif _inputsystem in ['apass']:
      col={}
      col['BV']=[(_catalogue2['B'][i]-_catalogue2['V'][i]) if (_catalogue2['B'][i]<99 and _catalogue2['V'][i]<99) else  (_catalogue2['B'][i]-_catalogue2['B'][i]) for i in range(0,len(_catalogue2['V']))]
      col['gr']=[(_catalogue2['g'][i]-_catalogue2['r'][i]) if (_catalogue2['g'][i]<99 and _catalogue2['r'][i]<99) else  (_catalogue2['g'][i]-_catalogue2['g'][i]) for i in range(0,len(_catalogue2['g']))]
      col['ri']=[(_catalogue2['r'][i]-_catalogue2['i'][i]) if (_catalogue2['r'][i]<99 and _catalogue2['i'][i]<99) else  (_catalogue2['r'][i]-_catalogue2['r'][i]) for i in range(0,len(_catalogue2['r']))]
      _catalogue2['B']=_catalogue2['B']-colorefisso['BBV']*np.array(col['BV']) #(_catalogue['B']-_catalogue['V'])
      _catalogue2['V']=_catalogue2['V']-colorefisso['BBV']*np.array(col['BV']) #(_catalogue['B']-_catalogue['V'])
      _catalogue2['g']=_catalogue2['g']-colorefisso['ggr']*np.array(col['gr']) #(_catalogue['g']-_catalogue['r'])
      _catalogue2['r']=_catalogue2['r']-colorefisso['rri']*np.array(col['ri']) #(_catalogue['r']-_catalogue['i'])
      _catalogue2['i']=_catalogue2['i']-colorefisso['iri']*np.array(col['ri']) #(_catalogue['r']-_catalogue['i'])
      print 'transform '+str(_inputsystem)+' to natural system'
      print "Bn = B - "+str(colorefisso['BBV'])+" * (B-V)"
      print "Vn = V - "+str(colorefisso['BBV'])+" * (B-V)"
      print "gn = g' - "+str(colorefisso['ggr'])+" * (g'-g')"
      print "rn = r' - "+str(colorefisso['rri'])+" * (r'-i')"
      print "in = i' - "+str(colorefisso['iri'])+" * (r'-i')"
   return _catalogue2

##################################################################################

def zeronew(ZZ,maxiter=10,nn=5,verbose=False,show=False):
     #         compute first median and error
     import numpy as np
     median=np.median(ZZ)                    
     sigma=(np.percentile(ZZ,75)-np.percentile(ZZ,25))*1.349
     # cut around median and new median
     ZZcut=np.compress((ZZ < (median+nn*sigma)) & (ZZ>(median-nn*sigma)),ZZ)
     xx=np.arange(len(ZZ))
     mediancut=np.median(ZZcut)      
     sigmacut=(np.percentile(ZZcut,75)-np.percentile(ZZcut,25))*1.349
     cut=len(ZZ)-len(ZZcut)
     iter=0
     while iter < maxiter and len(ZZcut)>5 and cut>0:
          iter+=1
          if verbose:
               print iter
               print 'reject  '+str(cut)+' objects'  
               print 'number of object= '+str(len(ZZcut))
               print 'median=  '+str(mediancut)
               print 'sigma= '+str(sigmacut)
          # new cut around new median after rejection 
          ZZcut2=np.compress((ZZ < (mediancut+nn*sigmacut)) & (ZZ>(mediancut-nn*sigmacut)),ZZ)  

          median2=np.median(ZZcut2)
          sigma2=(np.percentile(ZZcut2,75)-np.percentile(ZZcut2,25))*1.349
          cut=len(ZZcut)-len(ZZcut2)
          if len(ZZcut2)>=5:
               ZZcut=ZZcut2
               sigmacut=sigma2
               mediancut=np.median(ZZcut2)
          if verbose:   
              print len(ZZcut2),sigmacut,mediancut
     if show:
          import matplotlib.pyplot as pl
          pl.ion()
          xxc=np.arange(len(ZZcut))
          pl.plot(xx,ZZ,'or')
          pl.plot(xxc,ZZcut,'b*')
          pl.draw()
          import time
          time.sleep(1)

     return ZZcut,sigmacut,mediancut

#######################################################################
def sloan2file(ra, dec, radius=10., mag1=13., mag2=20., output='sloan.cat'):
    '''download an SDSS catalog'''
    t = SDSS.query_sql('''select P.ra, P.dec, P.objID, P.u, P.err_u, P.g, P.err_g, P.r, P.err_r, P.i, P.err_i, P.z, P.err_z
                          from PhotoPrimary as P, dbo.fGetNearbyObjEq({}, {}, {}) as N
                          where P.objID=N.objID and P.type=6 and P.r >= {} and P.r <= {}'''.format(ra, dec, radius, mag1, mag2))
    if t is not None:
        t['ra'].format ='%16.12f'
        t['dec'].format = '%16.13f'
        t['objID'].format = '%19d'
        for filt in 'ugriz':
            t[filt].format = '%8.5f'
            t['err_'+filt].format = '%11.9f'
        t.meta['comments'] = [
        'BEGIN CATALOG HEADER',
        '   type btext',
        '   nheader 1',
        '       csystem J2000',
        '   nfields 13',
        '       ra     1 0 d degrees ' + t['ra'].format,
        '       dec    2 0 d degrees ' + t['dec'].format,
        '       id     3 0 c INDEF   ' + t['objID'].format,
        '       u      4 0 r INDEF   ' + t['u'].format,
        '       uerr   5 0 r INDEF   ' + t['err_u'].format,
        '       g      6 0 r INDEF   ' + t['g'].format,
        '       gerr   7 0 r INDEF   ' + t['err_g'].format,
        '       r      8 0 r INDEF   ' + t['r'].format,
        '       rerr   9 0 r INDEF   ' + t['err_r'].format,
        '       i     10 0 r INDEF   ' + t['i'].format,
        '       ierr  11 0 r INDEF   ' + t['err_i'].format,
        '       z     12 0 r INDEF   ' + t['z'].format,
        '       zerr  13 0 r INDEF   ' + t['err_z'].format,
        'END CATALOG HEADER'
        ]
        t.write(output, format='ascii.no_header')
        print len(t), 'matching objects. Catalog saved to', output
    else:
        print 'No matching objects.'


def panstarrs2file(ra, dec, radius=20., mag1=13., mag2=20., output='panstarrs.cat'):
    '''
    Download a Pan-STARRS1 DR1 catalog from Vizier
    '''
    from astroquery.vizier import Vizier
    coord = SkyCoord(ra=ra, dec=dec, unit=(u.degree, u.degree))
    Vizier.ROW_LIMIT=-1
    Vizier.columns = ['raMean', 'decMean', 
                      'objID', 
                      'gFlags',
                      'yMeanPSFMag', 'yMeanPSFMagErr', #I'm going to make this u as a pipeline placeholder so this looks like SDSS
                      'gMeanPSFMag', 'gMeanPSFMagErr', 
                      'rMeanPSFMag', 'rMeanPSFMagErr', 
                      'iMeanPSFMag', 'iMeanPSFMagErr', 
                      'zMeanPSFMag', 'zMeanPSFMagErr']
    Vizier.column_filters={'nDetections': '>5',
                                                 'rMeanPSFMag-rMeanKronMag': '<0.05',
                                                 'gQfPerfect': '>0.85',
                                                 'rQfPerfect':'>0.85',
                                                 'iQfPerfect':'>0.85',
                                                 'zQfPerfect':'>0.85',
                                                 'rMeanPSFMag':'>{:f}'.format(mag1),
                                                 'rMeanPSFMag':'<={:f}'.format(mag2)}
    t = Vizier.query_region(coord,
                                 radius=float('{:f}'.format(radius))*u.arcmin,
                                 catalog='II/349')
    t = t[0]

    #From: https://outerspace.stsci.edu/display/PANSTARRS/PS1+Object+Flags#PS1ObjectFlags-ObjectFilterFlagsvalues,e.g.,columngFlagsintableMeanObject
    # 8: Ubercal photometry used in average measurement.
    # 16: PS1 photometry used in average measurement.
    # 32: PS1 stack photometry exists.
    # 256: Average magnitude uses only rank 0 detections.
    # 16384: PS1 stack photometry comes from primary skycell.
    # 32768: PS1 stack best measurement is a detection (not forced).
    # 16777216: Extended in this band.
    good_dq = 8+16+32+256+16384+32768
    extended_dq = 16777216
    keep_indx = (t['gFlags']&good_dq==good_dq) & (t['gFlags']&extended_dq != extended_dq)
    t = t[keep_indx]
    t.remove_column('gFlags')
    t.rename_column('ymag', 'umag')
    t.rename_column('e_ymag', 'e_umag')
    t['umag'] = 9999.
    t['e_umag'] = 9999.
    if t is not None:
        t['RAJ2000'].format ='%16.12f'
        t['DEJ2000'].format = '%16.13f'
        t['objID'].format = '%19d'
        for filt in 'griz':
            t[filt + 'mag'].format = '%8.5f'
            t['e_' + filt + 'mag'].format = '%11.9f'
        t.meta['comments'] = [
        'BEGIN CATALOG HEADER',
        '   type btext',
        '   nheader 1',
        '       csystem J2000',
        '   nfields 111',
        '       ra     1 0 d degrees ' + t['RAJ2000'].format,
        '       dec    2 0 d degrees ' + t['DEJ2000'].format,
        '       id     3 0 c INDEF   ' + t['objID'].format,
        '       u      4 0 r INDEF   ' + t['umag'].format,
        '       uerr   5 0 r INDEF   ' + t['e_umag'].format,
        '       g      6 0 r INDEF   ' + t['gmag'].format,
        '       gerr   7 0 r INDEF   ' + t['e_gmag'].format,
        '       r      8 0 r INDEF   ' + t['rmag'].format,
        '       rerr   9 0 r INDEF   ' + t['e_rmag'].format,
        '       i     10 0 r INDEF   ' + t['imag'].format,
        '       ierr  11 0 r INDEF   ' + t['e_imag'].format,
        '       z     12 0 r INDEF   ' + t['zmag'].format,
        '       zerr  13 0 r INDEF   ' + t['e_zmag'].format,
        'END CATALOG HEADER'
        ]
        t.write(output, format='ascii.no_header', overwrite=True)
        print len(t), 'matching objects. Catalog saved to', output
    else:
        print 'No matching objects.'


def gaia2file(ra, dec, size=26., mag_limit=18., output='gaia.cat'):

    from astroquery.gaia import Gaia

    warnings.simplefilter('ignore')  # suppress a lot of astroquery warnings

    coord = SkyCoord(ra=ra, dec=dec, unit=(u.degree, u.degree))
    height = u.Quantity(size, u.arcminute)
    width  = u.Quantity(size/np.cos(dec*np.pi/180.), u.arcminute)
    response = Gaia.query_object_async(coordinate=coord, width=width, height=height)

    response = response[
            (response['phot_g_mean_mag'] < mag_limit) &
            (response['astrometric_excess_noise_sig'] < 2) # filter objects with bad astrometry (e.g. HII regions in galaxies)
    ]
    response['ra'].format ='%16.12f'
    response['dec'].format = '%16.12f'
    response['phot_g_mean_mag'].format = '%.2f'
    
    try:
        gaia_cat = response['ra', 'dec', 'source_id', 'phot_g_mean_mag']
        gaia_cat.write(output, format='ascii.commented_header',
                delimiter=' ', overwrite=True)
    except ValueError:
        gaia_cat = response['ra', 'dec', 'SOURCE_ID', 'phot_g_mean_mag']
        gaia_cat.write(output, format='ascii.commented_header',
                delimiter=' ', overwrite=True)