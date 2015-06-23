import pyfits
import os
import numpy as np
import lsc

def MJDnow(datenow='',verbose=False):
   import datetime
   import time
   _JD0=55927.
   if not datenow:
      datenow=datetime.datetime(time.gmtime().tm_year, time.gmtime().tm_mon, time.gmtime().tm_mday, time.gmtime().tm_hour, time.gmtime().tm_min, time.gmtime().tm_sec)
   _JDtoday=_JD0+(datenow-datetime.datetime(2012, 01, 01,00,00,00)).seconds/(3600.*24)+\
             (datenow-datetime.datetime(2012, 01, 01,00,00,00)).days
   if verbose: print 'JD= '+str(_JDtoday)
   return _JDtoday


def SDSS_gain_dark(camcol, ugriz, run):
    if camcol == 1:
        if ugriz == 'u':
            gain = 1.62
            dark = 9.61
        elif ugriz == 'g':
            gain = 3.32
            dark = 15.6025
        elif ugriz == 'r':
            gain = 4.71
            dark = 1.8225
        elif ugriz == 'i':
            gain = 5.165
            dark = 7.84
        elif ugriz == 'z':
            gain = 4.745
            dark = 0.81
        else:
            print 'ERROR in SDSS_dark_gain: UGRIZ not set!'
    elif camcol == 2:
        if ugriz == 'u':
            if run < 1100:
                gain = 1.595
            elif run > 1100:
                gain = 1.825
            else:
                print 'ERROR in SDSS_dark_gain: RUN not set!'
            dark = 12.6025
        elif ugriz == 'g':
                gain = 3.855
                dark = 1.44
        elif ugriz == 'r':
                gain = 4.6
                dark = 1.00
        elif ugriz == 'i':
            gain = 6.565
            if run < 1500:
                dark = 5.76
            elif run > 1500:
                dark = 6.25
            else:
                print 'ERROR in SDSS_dark_gain: RUN not set!'
        elif ugriz == 'z':
            gain = 5.155
            dark = 1.0
        else:
            print 'ERROR in SDSS_dark_gain: UGRIZ not set!'
    elif camcol == 3:
        if ugriz == 'u':
            gain = 1.59
            dark = 8.7025
        elif ugriz == 'g':
            gain = 3.845
            dark = 1.3225
        elif ugriz == 'r':
            gain =  4.72
            dark = 1.3225
        elif ugriz == 'i':
            gain = 4.86
            dark = 4.6225
        elif ugriz == 'z':
            gain = 4.885
            dark = 1.0
        else:
            print 'ERROR in SDSS_dark_gain: UGRIZ not set!'
    elif camcol == 4:
        if ugriz == 'u':
            gain = 1.6
            dark = 12.6025
        elif ugriz == 'g':
            gain = 3.995
            dark = 1.96
        elif ugriz == 'r':
            gain =  4.76
            dark = 1.3225
        elif ugriz == 'i':
            gain = 4.885
            if run < 1500:
                dark = 6.25
            elif run > 1500:
                dark = 7.5625
            else:
                print 'ERROR in SDSS_dark_gain: RUN not set!'
        elif ugriz == 'z':
            gain = 4.775
            if run < 1500:
                dark = 9.61
            elif run > 1500:
                dark = 12.6025
            else:
                print 'ERROR in SDSS_dark_gain: RUN not set!'
        else:
            print 'ERROR in SDSS_dark_gain: UGRIZ not set!'
    elif camcol == 5:
        if ugriz == 'u':
            gain = 1.47
            dark = 9.3025
        elif ugriz == 'g':
            gain = 4.05
            dark = 1.1025
        elif ugriz == 'r':
            gain = 4.725
            dark = 0.81
        elif ugriz == 'i':
            gain = 4.64
            dark = 7.84
        elif ugriz == 'z':
            gain = 3.48
            if run < 1500:
                dark = 1.8225
            elif run > 1500:
                dark = 2.1025
            else:
                print 'ERROR in SDSS_dark_gain: RUN not set!'
        else:
            print 'ERROR in SDSS_dark_gain: UGRIZ not set!'
    elif camcol == 6:
        if ugriz == 'u':
            gain = 2.17
            dark = 7.0225
        elif ugriz == 'g':
            gain = 4.035
            dark = 1.8225
        elif ugriz == 'r':
            gain = 4.895
            dark = 0.9025
        elif ugriz == 'i':
            gain = 4.76
            dark = 5.0625
        elif ugriz == 'z':
            gain = 4.69
            dark = 1.21
        else:
            print 'ERROR in SDSS_dark_gain: UGRIZ not set!'
    else:
        print 'ERROR in SDSS_dark_gain: CAMCOL is not set!'
    return gain, dark

def downloadsdss(_ra,_dec,_band,_radius=20):
    from astroquery.sdss import SDSS
    from astropy import coordinates as coords
    import astropy.units as u
    import pyfits
    import os
    import sys
    import string
    import numpy as np
    from scipy import interpolate
    pos = coords.SkyCoord(ra=float(_ra)*u.deg,dec=float(_dec)*u.deg)
    print 'pos=  ',pos
    xid = SDSS.query_region(pos, spectro=False, radius=_radius*u.arcsec)
    print xid
    if xid:
       pointing=[]
       for i in xid:
          if (i['run'],i['camcol'],i['field']) not in pointing:
             pointing.append((i['run'],i['camcol'],i['field']))
       filevec=[]
       print len(pointing)
       for _run in pointing:
          im = SDSS.get_images(run = _run[0], camcol = _run[1], field= _run[2], band= _band, cache=True)
          output1 = _band+'_SDSS_'+str(_run[0])+'_'+str(_run[1])+'_'+str(_run[2])+'.fits'
          output2 = _band+'_SDSS_'+str(_run[0])+'_'+str(_run[1])+'_'+str(_run[2])+'c.fits'
          if os.path.isfile(output1):
             os.system('rm '+output1)
          if os.path.isfile(output2):
             os.system('rm '+output2)
          im[0].writeto(output1)
#         im[0][0].writeto(output2)

          FITS_file = pyfits.open(output1)
          new_header = FITS_file[0].header
          camcol     = FITS_file[0].header['CAMCOL']  # camcol
          ugriz      = FITS_file[0].header['FILTER']  # ugriz filter
          run1        = FITS_file[0].header['RUN']     # run
          gain, dark_var = SDSS_gain_dark(camcol, ugriz, run1)
          new_header['gain']  = gain
          new_header['dark']  = dark_var
          new_header['BUNIT']  = 'counts'
          new_header['rdnoise']  = 2
          frame_image = FITS_file[0].data.transpose()
          allsky     = FITS_file[2].data['ALLSKY'].transpose()
          allsky     = allsky[:,:,0]
          xinterp    = FITS_file[2].data['XINTERP'].transpose()
          xinterp    = xinterp[:,0]
          yinterp    = FITS_file[2].data['YINTERP'].transpose()
          yinterp    = yinterp[:,0]
          sky_function = interpolate.interp2d(np.arange(allsky.shape[1]),\
                                              np.arange(allsky.shape[0]), allsky, kind='linear')
          sky_image    = sky_function(yinterp, xinterp) # in counts
          calib     = FITS_file[1].data #  nanomaggies per count
          calib_image = np.empty_like(frame_image)
          for i in np.arange(calib_image.shape[1]):
             calib_image[:,i] = calib
          # Calculate the error in the frame image for use fitting algorithms later.
          dn_image        = frame_image / calib_image + sky_image # counts
          dn_err_image    = np.sqrt(dn_image / gain + dark_var)
          frame_image_err = dn_err_image * calib_image
          pyfits.writeto(output2, dn_image.transpose(), new_header)
          filevec.append(output2)
          os.system('rm '+output1)
       return filevec
    else:
       return ''

def sdss_swarp(imglist,_telescope='spectral',_ra='',_dec='',output=''):
    import re
    import datetime
    import lsc
    import time
    hdr = pyfits.getheader(imglist[0])
    _filter = hdr.get('filter')
    filt={'U':'U','B':'B','V':'V','R':'R','I':'I','u':'up','g':'gp','r':'rp','i':'ip','z':'zs'}
    if _filter in filt.keys():
        _filter = filt[_filter]

    _camcol = hdr.get('CAMCOL')
    _gain   = hdr.get('gain')
    _ron   = hdr.get('rdnoise')
    if 'day-obs' in hdr:
        _dayobs = hdr.get('dayobs')
    else:
        _dayobs = re.sub('-','',hdr.get('date-obs'))
    if 'airmass' in hdr:
        _airmass = hdr.get('airmass')
    else:
        _airmass = 1
    if 'MJD-OBS' in hdr:
        _mjd = hdr.get('MJD-OBS')
    else:
        _mjd = MJDnow(datetime.datetime(int(str(_dayobs)[0:4]),int(str(_dayobs)[4:6]),int(str(_dayobs)[6:8])))
    if not _ra:
        _ra = hdr.get('CRVAL1')
    if not _dec:
        _dec = hdr.get('CRVAL2')
    if _telescope == 'spectral':
        pixelscale = 0.30104  # 2 meter
        _imagesize =  2020
    elif _telescope == 'sbig':
            pixelscale = 0.467  # 1 meter
            _imagesize =  2030
    elif _telescope == 'sinistro':
            pixelscale = 0.387  # 1 meter
            _imagesize =  4020
    if not output:
        output = _telescope+'_SDSS_'+str(_dayobs)+'_'+str(_filter)+'.fits'

    line = 'swarp ' + ' '.join(imglist) + ' -IMAGEOUT_NAME ' + str(output) + ' -WEIGHTOUT_NAME ' + \
                   re.sub('.fits', '', output) + '.weight.fits -RESAMPLE_DIR ' + \
                   './ -RESAMPLE_SUFFIX .swarptemp.fits -COMBINE Y -RESAMPLING_TYPE LANCZOS3 -VERBOSE_TYPE NORMAL ' +\
                   '-SUBTRACT_BACK Y  -INTERPOLATE Y -PIXELSCALE_TYPE MANUAL,MANUAL -COMBINE_TYPE MEDIAN -PIXEL_SCALE ' +\
                   str(pixelscale) + ',' + str(pixelscale) + ' -IMAGE_SIZE ' + str(_imagesize) + ',' +\
                   str(_imagesize) + ' -CENTER_TYPE MANUAL,MANUAL -CENTER ' + str(_ra) + ',' + str(_dec) +\
                   ' -RDNOISE_DEFAULT ' + str(_ron) + ' -GAIN_KEYWORD NONONO ' + '-GAIN_DEFAULT ' +\
                   str(_gain)

#    line2 = 'swarp ' + ' '.join(imglist) + ' -IMAGEOUT_NAME  ' + re.sub('.fits', '', output) + '.noise.fits' +\
#                    ' -WEIGHTOUT_NAME ' + re.sub('.fits', '', output) + '.mask.fits' +\
#                    ' -SM_MKNOISE Y -BPMAXWEIGHTFRAC 0.2 ' + '-BPADDFRAC2NOISE 0.1 -RESAMPLE_DIR' +\
#                    ' ./ -RESAMPLE_SUFFIX .swarptemp.fits -COMBINE Y -RESAMPLING_TYPE LANCZOS3 -VERBOSE_TYPE NORMAL '+\
#                    '-SUBTRACT_BACK N  -INTERPOLATE Y -PIXELSCALE_TYPE MANUAL,MANUAL -PIXEL_SCALE ' + str(pixelscale)+\
#                    ',' + str(pixelscale) + ' -IMAGE_SIZE ' + str(_imagesize) + ',' + str(_imagesize) + \
#                    ' -CENTER_TYPE MANUAL,MANUAL -CENTER ' + str(_ra) + ',' + str(_dec) + \
#                    ' -RDNOISE_DEFAULT ' + str(_ron) + ' -GAIN_KEYWORD NONONO -GAIN_DEFAULT ' + str(_gain)
    os.system(line)
    hd = pyfits.getheader(output)
    ar = pyfits.getdata(output)
    ar = np.where(ar <= 0, np.mean(ar[np.where(ar > 0)]), ar)

    keyw = ['FILTER','TELESCOP','DATE-OBS','gain','ron','saturate']
    for jj in keyw:
        try:
            hd.update(jj, hdr[jj], hdr.comments[jj])
        except:
            print 'problem',jj
            pass

    hd.update('L1FWHM', 9999, 'FHWM (arcsec) - computed with sectractor')
    hd.update('WCSERR', 0,    'Error status of WCS fit. 0 for no error')
    hd.update('MJD-OBS', _mjd,    'MJD')
    hd.update('RA',      _ra,    'RA')
    hd.update('DEC',     _dec,    'DEC')
    hd.update('RDNOISE',     _ron, 'read out noise')
    hd.update('TELESCOP', 'SDSS', 'The Name of the Telescope')
    hd.update('INSTRUME', 'SDSS', 'Instrument used')
    hd.update('PIXSCALE', pixelscale, '[arcsec/pixel] Nominal pixel scale on sky')
    hd.update('FILTER', _filter, 'Instrument used')
    hd.update('DAYOBS', _dayobs, 'day of observation')
    hd.update('AIRMASS', _airmass, 'day of observation')

    new_header = hd
    # sinistro images are rotated 180 degree
    if _telescope == 'sinistro':
       ar = np.rot90(np.rot90(ar))
       CD1_1 = hd['CD1_1']
       CD2_2 = hd['CD2_2']
       new_header['CD1_1']  = CD1_1*(-1)
       new_header['CD2_2']  = CD2_2*(-1)

    out_fits = pyfits.PrimaryHDU(header=new_header, data=ar)
    out_fits.writeto(output, clobber=True, output_verify='fix')
    _=lsc.display_image(output,2,True,'','')
    answ='no'
    while answ in ['no','n','N','No']:
       answ = raw_input('flip, rotate the image ((n)o, rotate 180 (r), flip (x), flip (y)) [n] ')
       if answ in ['180','r']:
          output = rotateflipimage(output,rot180=True,flipx=False,flipy=False)
       elif answ in ['x']:
          output = rotateflipimage(output,rot180=False,flipx=True,flipy=False)
       elif answ in ['y']:
          output = rotateflipimage(output,rot180=False,flipx=False,flipy=True)
       time.sleep(1)
       __ = lsc.display_image(output,2,True,'','')
       answ = raw_input('ok  ? [y/n] [n] ')
       if not answ:
          answ = 'n'          

    for img in imglist:
       os.system('rm '+img)
    return output

def rotateflipimage(img,rot180=False,flipx=False,flipy=False):
   import pyfits
   import os
   hd = pyfits.getheader(img)
   ar = pyfits.getdata(img)
   new_header = hd
   CD1_1 = hd['CD1_1']
   CD2_2 = hd['CD2_2']
   if rot180:
      new_header['CD1_1']  = CD1_1*(-1)
      new_header['CD2_2']  = CD2_2*(-1)
      ar = np.rot90(np.rot90(ar))
   if flipy:
      new_header['CD2_2']  = CD2_2*(-1)
      ar = np.flipud(ar)
   if flipx:
      new_header['CD1_1']  = CD1_1*(-1)
      ar = np.fliplr(ar)
   os.system('rm '+img)
   out_fits = pyfits.PrimaryHDU(header=new_header, data=ar)
   out_fits.writeto(img, clobber=True, output_verify='fix')
   return img

##################################################################################
def sloanimage(img):
   from lsc import readhdr, readkey3,deg2HMS,display_image
   _ = display_image(img,1,True,'','')
   hdr = readhdr(img)
   _ra = readkey3(hdr,'RA')
   _dec = readkey3(hdr,'DEC')
   _instrume = readkey3(hdr,'instrume')
   _filter = readkey3(hdr,'filter')
   filt={'up':'u','gp':'g','rp':'r','ip':'i','zs':'z'}

   if _filter in filt.keys():
      _band = filt[_filter]
   else:
      _band = _filter

   _radius = 1000
   #_ra,_dec = deg2HMS(_ra,_dec)
   print _ra,_dec,_band,_radius
   frames =  downloadsdss(_ra,_dec,_band, _radius)

   if _instrume in lsc.instrument0['spectral']:
      _telescope = 'spectral'
   elif _instrume in lsc.instrument0['sinistro']:
      _telescope = 'sinistro'
   elif _instrume in lsc.instrument0['sbig']:
      _telescope = 'sbig'

   out = sdss_swarp(frames,_telescope,_ra,_dec,'')
   return out

####################################################
#img = 'tmp/elp1m008-kb74-20141224-0071-e90.fits'
#img = 'tmp/lsc1m009-fl03-20150605-0170-e90.fits'
#img = 'tmp/ogg2m001-fs02-20140923-0060-e90.fits'
#output = sloanimage(img)
