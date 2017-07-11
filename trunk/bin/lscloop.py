#!/usr/bin/env python
description = "> process lsc data  "

import re
import numpy as np
from argparse import ArgumentParser
from datetime import datetime, timedelta
import lsc
from multiprocessing import Pool

def multi_run_cosmic(args):
    return lsc.myloopdef.run_cosmic(*args)


# ###########################################################################

if __name__ == "__main__":   # main program
    parser = ArgumentParser(description=description)
    parser.add_argument("-e", "--epoch", default='20121212', help='args.epoch to reduce')
    parser.add_argument("-T", "--telescope", default='all')
    parser.add_argument("-I", "--instrument", default='', help='kb, fl, fs, sinistro, sbig')
    parser.add_argument("-n", "--name", default='', help='object name')
    parser.add_argument("-d", "--id", default='')
    parser.add_argument("-f", "--filter", default='',
                        choices=['landolt', 'sloan', 'apass', 'u', 'g', 'r', 'i', 'z', 'U', 'B', 'V', 'R', 'I',
                                'u,g', 'g,r', 'g,r,i', 'g,r,i,z', 'r,i,z', 'U,B,V', 'B,V,R', 'B,V', 'B,V,R,I', 'V,R,I'])
    parser.add_argument("-F", "--force", action="store_true")
    parser.add_argument("-b", "--bad", default='', help='bad stage',
                        choices=['wcs', 'psf', 'psfmag', 'zcat', 'abscat', 'mag', 'goodcat', 'quality', 'cosmic', 'diff'])
    parser.add_argument("-s", "--stage", default='',
                        choices=['wcs', 'psf', 'psfmag', 'zcat', 'abscat', 'mag', 'local', 'getmag', 'merge', 'diff',
                                 'template', 'makestamp', 'apmag', 'cosmic', 'ingestsloan', 'ingestps1',
                                 'checkwcs', 'checkpsf', 'checkmag', 'checkquality', 'checkpos', 'checkcat',
                                 'checkmissing', 'checkfvd', 'checkcosmic', 'checkdiff'])
    parser.add_argument("-R", "--RA", default='')
    parser.add_argument("-D", "--DEC", default='')
    parser.add_argument("--RAS", default='')
    parser.add_argument("--DECS", default='')
    parser.add_argument("--RA0", default='')
    parser.add_argument("--DEC0", default='')
    parser.add_argument("-x", "--xord", default=3, type=int, help='x-order for bg fit')
    parser.add_argument("-y", "--yord", default=3, type=int, help='y-order for bg fit')
    parser.add_argument("--bkg", default=4., type=float, help='bkg radius for the fit')
    parser.add_argument("--size", default=7., type=float, help='size of the stamp for the fit')
    parser.add_argument("-t", "--threshold", default=5., type=float, help='Source detection threshold')
    parser.add_argument("-i", "--interactive", action="store_true")
    parser.add_argument("--show", action="store_true")
    parser.add_argument("-c", "--center", action="store_false", dest='recenter', help='do not recenter')
    parser.add_argument("--unfix", action="store_false", dest='fix', help='use a variable color term')
    parser.add_argument("--cutmag", default=99., type=float, help='magnitude instrumental cut for zeropoint')
    parser.add_argument("--field", default='', choices=['landolt', 'sloan', 'apass'])
    parser.add_argument("--ref", default='', help='get sn position from this file')
    parser.add_argument("--use-sextractor", action="store_true", help="use souces from sextractor for PSF instead of catalog")
    parser.add_argument("--catalogue", default='')
    parser.add_argument("--calib", default='', choices=['sloan', 'natural', 'sloanprime'])
    parser.add_argument("--type", choices=['fit', 'ph', 'mag'], default='fit', help='type of magnitude (PSF, aperture, apparent)')
    parser.add_argument("--standard", default='', help='use the zeropoint from this standard')
    parser.add_argument("--xshift", default=0, type=int, help='x-shift in the guess astrometry')
    parser.add_argument("--yshift", default=0, type=int, help='y-shift in the guess astrometry')
    parser.add_argument("--fwhm", default='', help='fwhm (in pixel)')
    parser.add_argument("--mode", choices=['sv', 'astrometry'], default='sv', help='mode for wcs')
    parser.add_argument("--combine", default=1e-10, type=float, help='range to combine (in days)')
    parser.add_argument("--datamax", type=int, help='data max for saturation (counts)')
    parser.add_argument("--datamin", type=int, help='data min for saturation (counts)')
    parser.add_argument("--filetype", choices=[1, 2, 3, 4], default=1, type=int, help='filetype 1 [single], 2 [merge], 3 [difference]')
    parser.add_argument("-o", "--output", default='', help='output file')
    parser.add_argument("--tempdate", default='19990101-20080101', help='template date')
    parser.add_argument("--temptel", default='', help='--temptel  template instrument')
    parser.add_argument("--normalize", choices=['i', 't'], default='i', help='normalize to image [i], template [t] (hotpants parameter)')
    parser.add_argument("--convolve", choices=['i', 't'], default='', help='force convolution with image [i], template [t] (hotpants parameter)')
    parser.add_argument("--z1", type=float)
    parser.add_argument("--z2", type=float)
    parser.add_argument("--groupidcode", type=int)
    parser.add_argument("--ps1frames", default='', help='list of ps1 frames (download them manually)')
    parser.add_argument('--zcatnew', action='store_true', help='use fitcol3 for the zero point and color term')
    parser.add_argument("--bgo", default=3., type=float, help=' bgo parameter for hotpants')
    parser.add_argument("-p", "--psf", default='', help='psf image for template')
    parser.add_argument("--mag", type=float, default=0., help='mag to subtract from template image')
    parser.add_argument("--uncleaned", action='store_false', dest='clean', help='do not use cosmic ray cleaned image as template')
    parser.add_argument("--subtract-mag-from-header", action='store_true', help='automatically subtract mag from header of template image')
    parser.add_argument("--fixpix", action="store_true", help='Run fixpix on the images before doing image subtraction')
    parser.add_argument("--nstars", type=int, default=6, help="number of stars used to make the PSF")
    parser.add_argument("--difftype", default='', choices=['0', '1', '0,1'], help='Choose hotpants or optimal subtraction; hotpants = 0, difftype = 1, both = 0,1')
    parser.add_argument("--multicore", default=8, type=int, help='numbers of cores')
    args = parser.parse_args()

    if args.stage == 'checkdiff':
        filetype = 3
    elif args.bad == 'diff':
        filetype = 1
    else:
        filetype = args.filetype        

    if args.field:
        field = args.field
    elif np.all([filt in ['U', 'B', 'V', 'R', 'I', 'landolt'] for filt in args.filter.split(',')]):
        field = 'landolt'
    elif np.all([filt in ['u', 'g', 'r', 'i', 'z', 'sloan'] for filt in args.filter.split(',')]):
        field = 'sloan'
    else:
        field = 'apass'        

    if not _stage or _stage in ['local', 'getmag', 'wcs', 'psf', 'psfmag', 'makestamp', 'cosmic', 'apmag', 'ingestsloan', 'ingestps1',
            'checkwcs', 'checkpsf', 'checkmag', 'checkquality', 'checkpos', 'checkcat', 'checkmissing', 'checkfvd', 'checkcosmic', 'checkdiff']:
        ll = lsc.myloopdef.get_list(args.epoch, args.telescope, args.filter, args.bad, args.name, args.id, args.RA, args.DEC, 
                                    'photlco', filetype, args.groupidcode, args.instrument, args.temptel, args.difftype)
        if ll:
            print '##' * 50
            print '# IMAGE                                    OBJECT           FILTER           WCS            ' \
                  ' PSF           PSFMAG    APMAG       ZCAT          MAG      ABSCAT'
            for i in range(0, len(ll['filename'])):
                try:
                    print '%s\t%12s\t%9s\t%9s\t%9s\t%9s\t%9s\t%9s\t%9s\t%9s' % \
                          (ll['filename'][i].replace('.fits', ''), ll['objname'][i], ll['filter'][i],
                           str(ll['wcs'][i]), ll['psf'][i].replace('.fits', ''),
                           str(round(ll['psfmag'][i], 4)), str(round(ll['apmag'][i], 4)), ll['zcat'][i].replace('.cat', ''),
                           str(round(ll['mag'][i], 4)), ll['abscat'][i].replace('.cat', ''))
                except:
                    print '%s\t%12s\t%9s\t%9s\t%9s\t%9s\t%9s\t%9s\t%9s\t%9s' % \
                          (ll['filename'][i].replace('.fits', ''), ll['objname'][i], ll['filter'][i],
                           str(ll['wcs'][i]), ll['psf'][i],
                           str(ll['psfmag'][i]), str(ll['apmag'][i]), ll['zcat'][i].replace('.cat', ''),
                           str(ll['mag'][i]), ll['abscat'][i])
            print '\n###  total number = ' + str(len(ll['filename']))
            # ####################################
            if args.stage == 'local':  # calibrate local sequence from .cat files
                lsc.myloopdef.run_local(ll['filename'], field, args.interactive)
            elif args.stage == 'getmag':  # get final magnitude from mysql
                lsc.myloopdef.run_getmag(ll['filename'], args.output, args.interactive, args.show, args.combine, args.type)
            elif args.stage == 'psf':
                lsc.myloopdef.run_psf(ll['filename'], args.threshold, args.interactive, args.fwhm, args.show, args.force, args.fix, args.catalogue, 'photlco', args.use_sextractor, args.datamax, args.nstars)
            elif args.stage == 'psfmag':
                lsc.myloopdef.run_fit(ll['filename'], args.RAS, args.DECS, args.xord, args.yord, args.bkg, args.size, args.recenter, args.ref,
                                      args.interactive, args.show, args.force, args.datamax,args.datamin,'photlco',args.RA0,args.DEC0)
            elif args.stage == 'wcs':
                lsc.myloopdef.run_wcs(ll['filename'], args.interactive, args.force, args.xshift, args.xshift, args.catalogue,'photlco',args.mode)
            elif args.stage == 'makestamp':
                lsc.myloopdef.makestamp(ll['filename'], 'photlco', args.z1, args.z2, args.interactive, args.force, args.output)
            elif args.stage == 'apmag':
                lsc.myloopdef.run_apmag(ll['filename'], 'photlco')
            elif args.stage == 'cosmic':
                listfile = [k + v for k, v in zip(ll['filepath'], ll['filename'])]
                if args.multicore > 1:
                    p = Pool(args.multicore)
                    inp = [([i], 'photlco', 4.5, 0.2, 4,args.force) for i in listfile]
                    p.map(multi_run_cosmic, inp)
                    p.close()
                    p.join()
                else:
                    lsc.myloopdef.run_cosmic(listfile, 'photlco', 4.5, 0.2, 4, args.force)
            elif args.stage == 'ingestsloan':
                listfile = [k + v for k, v in zip(ll['filepath'], ll['filename'])]
                lsc.myloopdef.run_ingestsloan(listfile, 'sloan', show=args.show, force=args.force)
            elif args.stage == 'ingestps1':
                listfile = [k + v for k, v in zip(ll['filepath'], ll['filename'])]
                lsc.myloopdef.run_ingestsloan(listfile, 'ps1', args.ps1frames, show=args.show, force=args.force)
            elif args.stage in ['abscat', 'mag']:  # compute magnitudes for sequence stars or supernova
                if args.stage == 'mag':
                    catalogue = None
                elif args.catalogue:
                    catalogue = args.catalogue
                else:
                    catalogue = lsc.util.getcatalog(args.name, 'apass')
                if args.standard:
                    mm = lsc.myloopdef.filtralist(ll0, args.filter, '', args.standard, '', '', '', filetype, args.groupidcode, args.instrument, args.temptel, args.difftype)
                    extlist = mm['filename']
                    if not len(extlist):
                        raise Exception('no standard fields found')
                    for i in range(len(extlist)):
                        print '%s\t%12s\t%9s\t%9s\t%9s\t%9s\t%9s\t%9s\t%9s' % \
                              (str(mm['filename'][i]), str(mm['objname'][i]), str(mm['filter'][i]),
                               str(mm['wcs'][i]), str(mm['psf'][i]),
                               str(mm['psfmag'][i]), str(mm['zcat'][i]), str(mm['mag'][i]),
                               str(mm['abscat'][i]))
                else:
                    extlist = []
                lsc.myloopdef.run_cat(ll['filename'], extlist, args.interactive, args.stage, args.type, 'photlco', field, catalogue, args.force)
            elif args.stage == 'diff':  #    difference images using hotpants
                _difftypelist = args.difftype.split(',')
                for difftype in _difftypelist:
                    if not args.name:
                        raise Exception('you need to select one object: use option -n/--name')
                    if args.telescope=='all':
                        raise Exception('you need to select one type of instrument -T [fs, fl ,kb]')
                    
                    startdate = args.tempdate.split('-')[0]
                    enddate   = args.tempdate.split('-')[-1]

                    if difftype == '1':
                        suffix = '.optimal.{}.diff.fits'.format(args.temptel).replace('..', '.')
                    else:
                        suffix = '.{}.diff.fits'.format(args.temptel).replace('..', '.')

                    if args.temptel.upper() in ['SDSS', 'PS1']:
                        if args.telescope == 'kb':
                            fake_temptel = 'sbig'
                        elif args.telescope == 'fs':
                            fake_temptel = 'spectral'
                        elif args.telescope == 'fl':
                            fake_temptel = 'sinistro'
                    elif args.temptel:
                        fake_temptel = args.temptel
                    else:
                        fake_temptel = args.telescope

                    lista = lsc.mysqldef.getlistfromraw(lsc.myloopdef.conn, 'photlco', 'dayobs', startdate, enddate, '*', fake_temptel)
                    if lista:
                        ll00 = {}
                        for jj in lista[0].keys():
                            ll00[jj] = []
                        for i in range(0, len(lista)):
                            for jj in lista[0].keys():
                                ll00[jj].append(lista[i][jj])
                        inds = np.argsort(ll00['mjd'])  #  sort by mjd
                        for i in ll00.keys():
                            ll00[i] = np.take(ll00[i], inds)
                        lltemp = lsc.myloopdef.filtralist(ll00, args.filter, '', args.name, args.RA, args.DEC, '', 4, args.groupidcode, '')

                    if not lista or not lltemp:
                        raise Exception('template not found')

                    listtar = [k + v for k, v in zip(ll['filepath'], ll['filename'])]
                    listtemp = [k + v for k, v in zip(lltemp['filepath'], lltemp['filename'])]

                    lsc.myloopdef.run_diff(np.array(listtar), np.array(listtemp), args.show, args.force, args.normalize, args.convolve, args.bgo, args.fixpix, difftype, suffix)
            elif args.stage == 'template':  #    merge images using lacos and swarp
                listfile = [k + v for k, v in zip(ll['filepath'], ll['filename'])]
                lsc.myloopdef.run_template(np.array(listfile), args.show, args.force, args.interactive, args.RA, args.DEC, args.psf, args.mag, args.clean, args.subtract_mag_from_header)
            elif args.stage == 'checkpsf':
                lsc.myloopdef.checkpsf(ll['filename'])
            elif args.stage == 'checkmag':
                lsc.myloopdef.checkmag(ll['filename'], args.datamax)
            elif args.stage == 'checkwcs':
                lsc.myloopdef.checkwcs(ll['filename'], args.force, 'photlco', args.z1, args.z2)
            elif args.stage == 'checkfast':
                lsc.myloopdef.checkfast(ll['filename'], args.force)
            elif args.stage == 'checkquality':
                lsc.myloopdef.checkquality(ll['filename'])
            elif args.stage == 'checkpos':
                lsc.myloopdef.checkpos(ll['filename'], args.RA, args.DEC)
            elif args.stage == 'checkcat':
                lsc.myloopdef.checkcat(ll['filename'])
            elif args.stage == 'checkmissing':
                lsc.myloopdef.check_missing(ll['filename'])
            elif args.stage == 'checkfvd':
                lsc.myloopdef.checkfilevsdatabase(ll)
            elif args.stage == 'checkcosmic':
                lsc.myloopdef.checkcosmic(ll['filename'])
            elif args.stage == 'checkdiff':
                lsc.myloopdef.checkdiff(ll['filename'])
        else:
            print '\n### no data selected'
    # ################################################
    else:
        if _stage == 'diff':
            ll0 = lsc.myloopdef.get_list(args.epoch, args.telescope, args.filter, args.bad, args.name, args.id, args.RA, args.DEC,
                                         'photlco', filetype, args.groupidcode, args.instrument, args.temptel)
        else:
            ll0 = lsc.myloopdef.get_list(args.epoch, args.telescope, args.filter, args.bad, args.name, args.id, args.RA, args.DEC,
                                         'photlco', filetype, args.groupidcode, args.instrument, args.temptel, args.difftype)
        for epo in unique(ll0['dayobs']):
            print '\n#### ' + str(epo)
            ll = {key: val[ll0['dayobs'] == epo] for key, val in ll0.items()}
            if len(ll['filename']) > 0:
                # print '##'*50
                #                 print '# IMAGE                                    OBJECT           FILTER           WCS             PSF           PSFMAG          ZCAT          MAG      ABSCAT'
                for i in range(0, len(ll['filename'])):
                    print '%s\t%12s\t%9s\t%9s\t%9s\t%9s\t%9s\t%9s\t%9s' % \
                          (str(ll['filename'][i]), str(ll['objname'][i]), str(ll['filter'][i]), str(ll['wcs'][i]),
                           str(ll['psf'][i]),
                           str(ll['psfmag'][i]), str(ll['zcat'][i]), str(ll['mag'][i]), str(ll['abscat'][i]))
                print '\n###  total number = ' + str(len(ll['filename']))
                if args.stage == 'zcat':
                    if not args.name:
                        raise Exception('''name not selected, if you want to do zeropoint,
                                            you need to specify the name of the object''')

                    if args.catalogue:
                        catalogue = args.catalogue
                    else:
                        catalogue = lsc.util.getcatalog(args.name, field)

                    if field == 'apass':
                        filters_in_field = set('BVgri')
                    elif field == 'landolt':
                        filters_in_field = set('UBVRI')
                    elif field == 'sloan':
                        filters_in_field = set('ugriz')
                    else:
                        print 'warning: field not defined, zeropoint not computed'

                    filenames = [fn for fn, filt in zip(ll['filename'], ll['filter']) if lsc.sites.filterst1[filt] in filters_in_field]
                    filters_in_images = {lsc.sites.filterst1[filt] for filt in ll['filter']}
                    _color = ''.join(filters_in_images & filters_in_field)
                    if _color:
                        lsc.myloopdef.run_zero(filenames, args.fix, args.type, field, catalogue, _color, args.interactive, args.force, args.show, args.cutmag, 'photlco', args.calib, args.zcatnew)
                    else:
                        print 'none of your filters ({}) match the chosen catalog ({})'.format(''.join(filters_in_images), ''.join(filters_in_field))
                elif args.stage == 'merge':  #    merge images using lacos and swarp
                    listfile = [k + v for k, v in zip(ll['filepath'], ll['filename'])]
                    lsc.myloopdef.run_merge(np.array(listfile), args.force)
                else:
                    print _stage + ' not defined'
            else:
                print '\n### no data selected'
