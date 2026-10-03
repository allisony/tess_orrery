import numpy as np
import matplotlib.pyplot as plt
from glob import glob
import os
import datetime as dt
from diverging_map import diverge_map
import matplotlib.font_manager as fm
import pandas as pd
from matplotlib.patches import Ellipse

cd = os.path.abspath(os.path.dirname(__file__))

# Where the planet data come from: the NASA Exoplanet Archive's Planetary
# Systems (PS) table. Only the default parameter set for each planet
# (default_flag == 1) is used.
#   'download': fetch the current table from the archive. It is saved next to
#               this script as PS_<date>_<time>.csv so the run is reproducible
#               (switch to 'file' with that name to reuse it).
#   'file':     use a table you already downloaded (planetlist below).
data_source = 'file'

# file to use when data_source = 'file'. Give a full path if it isn't in the
# same folder as this script.
planetlist = os.path.join(cd, 'PS_2026.09.21_12.27.14.csv')

# If True, a system with at least one TESS-discovered planet is plotted with
# ALL of its confirmed planets (including ones found by RV, Kepler, etc.).
# If False, only the TESS-discovered planets themselves are plotted.
include_companions = False

# If True, drop planets not known to transit (tran_flag != 1), e.g. long-period
# RV companions that sneak in through include_companions.
transiting_only = True

# Eccentric orbits are drawn as ellipses (star at one focus) and planets move
# along them following Kepler's equation. Orbits with e below this value are
# drawn as circles, so catalog noise near e=0 doesn't distort everything.
# Set to 0 to use every catalog eccentricity, or to 1 to make all orbits
# circular as in the original orrery.
ecc_min = 0.1

# Drop any system whose largest orbit extends beyond this many AU from its
# star (apoastron). A single wide, eccentric orbit forces everything else
# away from it and leaves a big hole. None keeps everything.
max_apoastron = None

# minimum number of planets for a system to be plotted
# (Kepler orrery used multis only; set to 1 to include every TOI)
minplanets = 1

# are we loading in system locations from a previous file (None if not)
# The Kepler orrery_centers.txt is keyed on KIC numbers, so don't reuse it.
lcenfile = None
# if we're not loading a centers file,
# where do we want to save the one generated (None if don't save)
scenfile = os.path.join(cd, 'tess_orrery_centers.txt')

# add in the solar system to the plots
addsolar = True
# put it at a fixed location? otherwise use posinlist to place it
fixedpos = True
# fixed x and y positions (in AU) to place the Solar System
# if addsolar and fixedpos are True
ssx = 3.
ssy = 0.
# fraction of the way through the planet list to treat the solar system
# if fixedpos is False.
# 0 puts it first and near the center, 1 puts it last on the outside
posinlist = 0.2

# making rstart smaller or maxtry bigger takes longer but tightens the
# circle
# Radius of the circle (AU) to initially try placing a system
# when generating locations
rstart = 4.
# number of tries to randomly place a system at a given radius
# before expanding the circle
maxtry = 50
# minimum spacing between systems (AU)
# TESS systems are compact (mostly P < 30 d), so pack them tighter than Kepler
spacing = 0.15

# which font to use for the text
fontfile = os.path.join(cd, 'Avenir-Black.otf')
fontfam = 'normal'
fontcol = 'white'

# font sizes at various resolutions
fszs1 = {480: 12, 720: 14, 1080: 22}
fszs2 = {480: 15, 720: 17, 1080: 27}

# background color
bkcol = 'black'

# color and alpha for the circular orbit paths
orbitcol = '#424242'
orbitalpha = 1.

# add a background to the legend to distinguish it?
legback = True
# if so, use this color and alpha
legbackcol = bkcol
legalpha = 0.7

# are we making the png files for a movie or gif
makemovie = True
# resolution of the images. Currently support 480, 720 or 1080.
reso = 1080

# output directory for the images in the movie
# (will be created if it doesn't yet exist)
#outdir = os.path.join(cd, 'orrery-40s/')
outdir = os.path.join(cd, 'movie/')

# times to evaluate the planets at, in BTJD = BJD - 2457000
# TESS science operations began at ~BTJD 1325 (25 Jul 2018).
# The movie runs from tstart to tend (default: today).
tstart = 1325.
tend = tstart + 365*2.#(dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.datetime(2014, 12, 8, 12)).total_seconds() / 86400.
# days per frame. Kepler used 0.5. Larger steps make a shorter movie, but
# planets with P < 2*tstep will alias (appear to stand still or run backwards).
tstep = 0.5
times = np.arange(tstart, tend, tstep)
# number of frames to produce (seconds of movie = nframes / fps)
nframes = len(times)
print('{0} frames = {1:.1f} s at 30 fps'.format(nframes, nframes / 30.))

# camera path: start zoomed in on the Solar System, zoom out to show the
# whole field, then zoom back in somewhere else. 1 = whole field visible.
zoom_in = 0.45
# where to end zoomed in (AU, layout coordinates). None = the point opposite
# the Solar System across the center of the field.
endx, endy = None, None

# ===================================== #

# reference time for TESS data: BTJD 0 = BJD 2457000.0 = 8 Dec 2014 12:00
time0 = dt.datetime(2014, 12, 8, 12)

# the ID given to the solar system (TIC IDs are all positive)
kicsolar = -5

# load in the PS table. The archive's CSV starts with a block of '#' comment
# lines whose length depends on which columns were downloaded, so count them
# rather than hardcoding skiprows.
if data_source == 'download':
    from urllib.parse import quote
    cols = ('pl_name,hostname,tic_id,default_flag,disc_facility,tran_flag,'
            'pl_orbper,pl_tranmid,pl_orbsmax,pl_orbeccen,pl_orblper,'
            'pl_rade,pl_eqt,pl_insol,st_teff,st_rad,st_mass,st_logg')
    # all default parameter sets, so include_companions can find non-TESS
    # planets in TESS systems
    query = 'select {0} from ps where default_flag = 1'.format(cols)
    url = ('https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=' +
           quote(query) + '&format=csv')
    print('Downloading the PS table from the NASA Exoplanet Archive...')
    downloaded = pd.read_csv(url)
    planetlist = os.path.join(
        cd, dt.datetime.now().strftime('PS_%Y.%m.%d_%H.%M.%S.csv'))
    downloaded.to_csv(planetlist, index=False)
    print('Saved {0} planets to {1}'.format(len(downloaded),
                                             os.path.basename(planetlist)))
elif data_source != 'file':
    raise ValueError("data_source must be 'download' or 'file'")

if not os.path.exists(planetlist):
    raise FileNotFoundError('Planet table not found: ' + planetlist)
with open(planetlist) as ff:
    nskip = 0
    for line in ff:
        if not line.startswith('#'):
            break
        nskip += 1
all_planets = pd.read_csv(planetlist, skiprows=nskip)
pl = all_planets[all_planets['default_flag'] == 1]

# optional columns: if they weren't included in the download, fall back
for col, fill in [('pl_tranmid', np.nan), ('pl_orbeccen', np.nan),
                  ('pl_orblper', np.nan), ('pl_eqt', np.nan),
                  ('st_mass', np.nan), ('tic_id', np.nan)]:
    if col not in pl.columns:
        print('Note: column {0} not in {1}; using defaults'.format(
            col, os.path.basename(planetlist)))
        pl = pl.assign(**{col: fill})
if transiting_only and 'tran_flag' not in pl.columns:
    print('Note: tran_flag not in file; cannot remove non-transiting planets')
    transiting_only = False

# report how many planets survive each cut
print('\n--- Planet selection ---')
print('{0:6d} confirmed planets in the file (default parameter sets)'.format(
    len(pl)))
istess = pl['disc_facility'] == \
    'Transiting Exoplanet Survey Satellite (TESS)'
print('{0:6d} discovered by TESS'.format(istess.sum()))
if include_companions:
    pl = pl[pl['hostname'].isin(pl.loc[istess, 'hostname'])]
    print('{0:6d} after adding companions in TESS systems'.format(len(pl)))
else:
    pl = pl[istess]
if transiting_only:
    pl = pl[pl['tran_flag'] == 1]
    print('{0:6d} after removing non-transiting planets'.format(len(pl)))
pl = pl[pl['pl_orbper'] > 0].copy()
print('{0:6d} with a valid period'.format(len(pl)))

# system ID: the TIC number ('TIC 12345' -> 12345). Hosts without a TIC
# get a stable ID derived from the host name instead.
pl['tid'] = pd.to_numeric(pl['tic_id'].astype(str).str.replace('TIC', '')
                          .str.strip(), errors='coerce')
notic = ~np.isfinite(pl['tid'])
if notic.any():
    hostcodes = pd.factorize(pl['hostname'])[0]
    pl.loc[notic, 'tid'] = 1e10 + hostcodes[notic.values]

# semi-major axis: use the catalog value, else Kepler's third law from M*
semi_calc = (pl['st_mass'] * (pl['pl_orbper'] / 365.25) ** 2.) ** (1. / 3.)
semi_all = pl['pl_orbsmax'].fillna(semi_calc)

# fill missing equilibrium temperatures from Teff, R*, a (albedo 0)
teq_calc = pl['st_teff'] * np.sqrt(pl['st_rad'] * 0.00465047 /
                                    (2. * semi_all))
teq_all = pl['pl_eqt'].fillna(teq_calc)

kics = pl['tid'].values.astype(float)
hosts = pl['hostname'].values
pds = pl['pl_orbper'].values
# epochs in BTJD; missing epochs (e.g. non-transiting companions)
# just get a random phase
it0s = pl['pl_tranmid'].values.copy() - 2457000.
nofit = ~np.isfinite(it0s)
it0s[nofit] = np.random.rand(nofit.sum()) * pds[nofit]
radius = pl['pl_rade'].values
iteqs = teq_all.values
semi = semi_all.values
# eccentricity and argument of periastron (deg). Missing e -> circular;
# missing omega -> 90 deg (transit at periastron).
ecc = pl['pl_orbeccen'].fillna(0.).clip(0., 0.99).values.copy()
ecc[ecc < ecc_min] = 0.
omega = np.radians(pl['pl_orblper'].fillna(90.).values)

# grab the TICs with known parameters
good = (np.isfinite(semi) & np.isfinite(pds) &
        np.isfinite(radius) & np.isfinite(iteqs))

# breakdown of why planets are rejected
miss_a = ~np.isfinite(semi)
miss_p = ~np.isfinite(pds)
miss_r = ~np.isfinite(radius)
miss_t = ~np.isfinite(iteqs)
print('{0:6d} rejected for missing parameters:'.format((~good).sum()))
print('         {0:4d} missing a'.format(miss_a.sum()))
print('         {0:4d} missing P'.format(miss_p.sum()))
print('         {0:4d} missing Rp'.format(miss_r.sum()))
print('         {0:4d} missing Teq'.format(miss_t.sum()))
only_t = miss_t & ~miss_a & ~miss_p & ~miss_r
print('         {0:4d} missing ONLY Teq (a, P, Rp all present)'.format(
    only_t.sum()))
# Teq is filled from Teff, R*, and a when pl_eqt is blank, so a missing Teq
# means pl_eqt is blank AND at least one of those is too
print('              ({0} lack Teff, {1} lack R*)'.format(
    (only_t & ~np.isfinite(pl['st_teff'].values)).sum(),
    (only_t & ~np.isfinite(pl['st_rad'].values)).sum()))
# write the rejected planets and what each is missing to a file
rej = pd.DataFrame({'pl_name': pl['pl_name'].values, 'hostname': hosts,
                    'missing_a': miss_a, 'missing_P': miss_p,
                    'missing_Rp': miss_r, 'missing_Teq': miss_t,
                    'st_teff': pl['st_teff'].values,
                    'st_rad': pl['st_rad'].values,
                    'st_mass': pl['st_mass'].values})[~good]
rej.to_csv(os.path.join(cd, 'rejected_planets.csv'), index=False)
print('       (list saved to rejected_planets.csv)')

kics = kics[good]
hosts = hosts[good]
pds = pds[good]
it0s = it0s[good]
semi = semi[good]
radius = radius[good]
iteqs = iteqs[good]
ecc = ecc[good]
omega = omega[good]
print('{0:6d} with complete parameters (a, P, Rp, Teq)'.format(good.sum()))

# optionally drop systems with very wide orbits
apo_pl = semi * (1. + ecc)
if max_apoastron is not None:
    wide = np.unique(kics[apo_pl > max_apoastron])
    keep = ~np.isin(kics, wide)
    for arr in ['kics', 'hosts', 'pds', 'it0s', 'semi', 'radius', 'iteqs',
                'ecc', 'omega', 'apo_pl']:
        globals()[arr] = globals()[arr][keep]
    print('{0:6d} after dropping {1} systems with apoastron > {2} AU'.format(
        len(kics), len(wide), max_apoastron))

# report the widest systems, since they dominate the layout
print('\nWidest systems (largest apoastron):')
for k in np.argsort(apo_pl)[::-1][:5]:
    print('  {0:<20s} a = {1:6.2f} AU  e = {2:4.2f}  P = {3:8.1f} d  '
          'apo = {4:6.2f} AU'.format(str(hosts[k]), semi[k], ecc[k], pds[k],
                                     apo_pl[k]))


def system_geometry(kic):
    """Smallest-ish circle enclosing all orbits of a system.

    Returns (dx, dy, R): the star's offset from the circle's center, and the
    circle's radius, in AU. For eccentric orbits the star sits at a focus, so
    centering the exclusion circle on the star wastes a lot of space.
    """
    if kic == kicsolar:
        return 0., 0., 1.524
    fd = np.where(kics == kic)[0]
    ff = np.linspace(0., 2. * np.pi, 361)
    xs, ys = [], []
    for jj in fd:
        a, e = semi[jj], ecc[jj]
        # periastron direction in plot coordinates (see planet_xy)
        peri = omega[jj] - np.pi / 2.
        r = a * (1. - e ** 2.) / (1. + e * np.cos(ff))
        xs.append(r * np.cos(ff + peri))
        ys.append(r * np.sin(ff + peri))
    xs = np.concatenate(xs)
    ys = np.concatenate(ys)
    cx = (xs.max() + xs.min()) / 2.
    cy = (ys.max() + ys.min()) / 2.
    R = np.sqrt((xs - cx) ** 2. + (ys - cy) ** 2.).max()
    # star (at 0, 0) relative to the circle center
    return -cx, -cy, R


# if we've already decided where to put each system, load it up
if lcenfile is not None:
    multikics, xcens, ycens, maxsemis = np.loadtxt(lcenfile, unpack=True)
    nplan = len(multikics)
    geo = np.array([system_geometry(k) for k in multikics])
    cdx, cdy = geo[:, 0], geo[:, 1]
# otherwise figure out how to fit all the planets into a nice distribution
else:
    # we only want to plot multi-planet systems
    multikics, nct = np.unique(kics, return_counts=True)
    multikics = multikics[nct >= minplanets]
    maxsemis = multikics * 0.
    nplan = len(multikics)

    # the maximum size needed for each system
    for ii in np.arange(len(multikics)):
        # radius of the circle enclosing all of this system's orbits
        maxsemis[ii] = system_geometry(multikics[ii])[2]

    # place the biggest ones first so the small ones fill in the gaps.
    # Noise is in log space so ordering works whether systems are 0.05 AU
    # (most of TESS) or several AU across.
    inds = np.argsort(np.log10(maxsemis) +
                      np.random.randn(len(maxsemis)) * 0.3)[::-1]
    
    # place the smallest ones first, but add uniform noise
    # so they aren't perfectly in order
    #inds = np.argsort(maxsemis + np.random.uniform(low=-2, high=2, size=len(maxsemis)))[::-1]
    
    # purely random order
    #np.random.shuffle(inds)
    
    # biggest ones first, small ones fill in
    #bigs = np.where(maxsemis > 1.)[0]
    #smalls = np.where(maxsemis <= 1.)[0]
    #np.random.shuffle(smalls)
    #inds = np.concatenate((bigs, smalls))

    # reorder to place them
    maxsemis = maxsemis[inds]
    multikics = multikics[inds]

    # add in the solar system if desired
    if addsolar:
        nplan += 1
        # we know where we want the solar system to be placed, place it first
        if fixedpos:
            insind = 0
        # otherwise treat it as any other system
        # and place it at this point through the list
        else:
            insind = int(posinlist * len(maxsemis))

        maxsemis = np.insert(maxsemis, insind, 1.524)
        multikics = np.insert(multikics, insind, kicsolar)

    # Systems are scattered within an ellipse with the movie's 16:9 shape, so
    # the layout fills the frame naturally. (The original code instead
    # rejected positions that made the overall aspect ratio wrong, which
    # could only be fixed late in the placement by flinging a system far
    # out to one side, leaving isolated stragglers.)
    layout_ratio = 16. / 9.
    xstretch = np.sqrt(layout_ratio)
    ystretch = 1. / np.sqrt(layout_ratio)

    xcens = np.array([])
    ycens = np.array([])
    # place all the planets without overlapping or violating aspect ratio
    for ii in np.arange(nplan):
        # reset the counters
        repeat = True
        r0 = rstart * 1.
        ct = 0
        ratio = 1.

        # progress bar
        if (ii % 20) == 0:
            print('Placing {0} of {1} systems'.format(ii, nplan))

        # put the solar system at its fixed position if desired
        if multikics[ii] == kicsolar and fixedpos:
            xcens = np.concatenate((xcens, [ssx]))
            ycens = np.concatenate((ycens, [ssy]))
            repeat = False
        else:
            xcens = np.concatenate((xcens, [0.]))
            ycens = np.concatenate((ycens, [0.]))

        # repeat until we find an open location for this system
        while repeat:
            # pick a random radius (up to our limit) and angle
            r = np.random.rand() * r0
            theta = np.random.rand() * 2. * np.pi
            xcens[ii] = r * np.cos(theta) * xstretch
            ycens[ii] = r * np.sin(theta) * ystretch

            # how far apart are all systems
            dists = np.sqrt((xcens - xcens[ii]) ** 2. +
                            (ycens - ycens[ii]) ** 2.)
            rsum = maxsemis + maxsemis[ii]

            # systems that overlap
            bad = np.where(dists < rsum[:ii + 1] + spacing)

            # accept the spot if it doesn't overlap any placed system
            if len(bad[0]) == 1:
                repeat = False

            # if we've been trying to place this system but can't get it
            # at this radius, expand the search zone
            if ct > maxtry:
                ct = 0
                # add equal area every time
                r0 = np.sqrt(rstart ** 2. + r0 ** 2.)

            ct += 1

    # placement was done on the enclosing circles; convert to star positions
    geo = np.array([system_geometry(k) for k in multikics])
    cdx, cdy = geo[:, 0], geo[:, 1]
    xcens = xcens + cdx
    ycens = ycens + cdy

    # save this placement distribution if desired (star positions)
    if scenfile is not None:
        np.savetxt(scenfile,
                   np.column_stack((multikics, xcens, ycens, maxsemis)),
                   fmt=['%d', '%f', '%f', '%f'])

plt.close('all')

# make a diagnostic plot showing the distribution of systems
fig = plt.figure()
plt.xlim((xcens - cdx - maxsemis).min(), (xcens - cdx + maxsemis).max())
plt.ylim((ycens - cdy - maxsemis).min(), (ycens - cdy + maxsemis).max())
plt.gca().set_aspect('equal', adjustable='box')
plt.xlabel('AU')
plt.ylabel('AU')

for ii in np.arange(nplan):
    c = plt.Circle((xcens[ii] - cdx[ii], ycens[ii] - cdy[ii]), maxsemis[ii],
                   clip_on=False, alpha=0.3)
    fig.gca().add_artist(c)

# all of the parameters we need for the plot
t0s = np.array([])
periods = np.array([])
semis = np.array([])
eccs = np.array([])
omegas = np.array([])
radii = np.array([])
teqs = np.array([])
usedkics = np.array([])
fullxcens = np.array([])
fullycens = np.array([])

for ii in np.arange(nplan):
    # known solar system parameters
    if addsolar and multikics[ii] == kicsolar:
        usedkics = np.concatenate((usedkics, np.ones(8) * kicsolar))
        # always start the outer solar system in the same places
        # for optimial visibility
        # inner-planet epochs were in BKJD; shift them to BTJD
        dbk = 2457000. - 2454833.
        t0s = np.concatenate((t0s, [85. - dbk, 192. - dbk, 266. - dbk,
                                    180. - dbk,
                                    times[0] - 3. * 4332.8 / 4,
                                    times[0] - 22. / 360 * 10755.7,
                                    times[0] - 30687 * 145. / 360,
                                    times[0] - 60190 * 202. / 360]))
        periods = np.concatenate((periods, [87.97, 224.70, 365.26, 686.98,
                                            4332.8, 10755.7, 30687, 60190]))
        semis = np.concatenate((semis, [0.387, 0.723, 1.0, 1.524, 5.203,
                                        9.537, 19.19, 30.07]))
        eccs = np.concatenate((eccs, np.zeros(8)))
        omegas = np.concatenate((omegas, np.zeros(8) + np.pi / 2.))
        radii = np.concatenate((radii, [0.383, 0.95, 1.0, 0.53, 10.86, 9.00,
                                        3.97, 3.86]))
        teqs = np.concatenate((teqs, [409, 299, 255, 206, 200,
                                      200, 200, 200]))
        fullxcens = np.concatenate((fullxcens, np.zeros(8) + xcens[ii]))
        fullycens = np.concatenate((fullycens, np.zeros(8) + ycens[ii]))
        continue

    fd = np.where(kics == multikics[ii])[0]
    # get the values for this system
    usedkics = np.concatenate((usedkics, kics[fd]))
    t0s = np.concatenate((t0s, it0s[fd]))
    periods = np.concatenate((periods, pds[fd]))
    semis = np.concatenate((semis, semi[fd]))
    eccs = np.concatenate((eccs, ecc[fd]))
    omegas = np.concatenate((omegas, omega[fd]))
    radii = np.concatenate((radii, radius[fd]))
    teqs = np.concatenate((teqs, iteqs[fd]))
    fullxcens = np.concatenate((fullxcens, np.zeros(len(fd)) + xcens[ii]))
    fullycens = np.concatenate((fullycens, np.zeros(len(fd)) + ycens[ii]))

# sort by radius so that the large planets are on the bottom and
# don't cover smaller planets
# summary of what actually appears in the movie (excluding the Solar System)
notsolar = usedkics != kicsolar
sysids, npl = np.unique(usedkics[notsolar], return_counts=True)
print('\n--- Included in the movie ---')
if minplanets > 1:
    print('(only systems with >= {0} planets; '
          'set minplanets = 1 to include all)'.format(minplanets))
print('{0:6d} planets'.format(notsolar.sum()))
print('{0:6d} systems'.format(len(sysids)))
for nn in np.unique(npl):
    print('{0:6d} systems with {1} planet{2}'.format(
        (npl == nn).sum(), nn, '' if nn == 1 else 's'))
print('{0:6d} planets on orbits with e >= {1}'.format(
    (eccs[notsolar] > 0).sum(), ecc_min))
print()

rs = np.argsort(radii)[::-1]
usedkics = usedkics[rs]
t0s = t0s[rs]
periods = periods[rs]
semis = semis[rs]
eccs = eccs[rs]
omegas = omegas[rs]
radii = radii[rs]

# --- Keplerian orbits ---
# Convention: angles in the plot are measured so that a planet sits at
# angle 0 (+x from its star) at mid-transit, matching the circular orrery.
# Transit happens at true anomaly f_tr = pi/2 - omega, so the plot angle is
# theta = f - f_tr, and periastron points along theta = -f_tr.
f_tr = np.pi / 2. - omegas
# mean anomaly at transit
E_tr = 2. * np.arctan(np.sqrt((1. - eccs) / (1. + eccs)) * np.tan(f_tr / 2.))
M_tr = E_tr - eccs * np.sin(E_tr)


def planet_xy(time):
    """Sky-plane (top-down) positions of every planet at a given BTJD."""
    M = M_tr + 2. * np.pi * (time - t0s) / periods
    M = np.mod(M, 2. * np.pi)
    # solve Kepler's equation M = E - e sin E with Newton's method
    E = M + eccs * np.sin(M)
    for _ in range(30):
        dE = (E - eccs * np.sin(E) - M) / (1. - eccs * np.cos(E))
        E -= dE
        if np.abs(dE).max() < 1e-10:
            break
    f = 2. * np.arctan2(np.sqrt(1. + eccs) * np.sin(E / 2.),
                        np.sqrt(1. - eccs) * np.cos(E / 2.))
    r = semis * (1. - eccs * np.cos(E))
    theta = f - f_tr
    return fullxcens + r * np.cos(theta), fullycens + r * np.sin(theta)


teqs = teqs[rs]
fullxcens = fullxcens[rs]
fullycens = fullycens[rs]

if makemovie:
    plt.ioff()
else:
    plt.ion()

# create the figure at the right size (this assumes a default pix/inch of 100)
figsizes = {480: (8.54, 4.8), 720: (8.54, 4.8), 1080: (19.2, 10.8)}
fig = plt.figure(figsize=figsizes[reso])

# make the plot cover the entire figure with the right background colors
ax = fig.add_axes([0.0, 0, 1, 1])
ax.axis('off')
fig.patch.set_facecolor(bkcol)
ax.patch.set_facecolor(bkcol)

# exact bounding box of each drawn ellipse, for setting the figure limits
_peri = -f_tr
_b = semis * np.sqrt(1. - eccs ** 2.)
ell_cx = fullxcens - semis * eccs * np.cos(_peri)
ell_cy = fullycens - semis * eccs * np.sin(_peri)
ell_hx = np.sqrt((semis * np.cos(_peri)) ** 2. + (_b * np.sin(_peri)) ** 2.)
ell_hy = np.sqrt((semis * np.sin(_peri)) ** 2. + (_b * np.cos(_peri)) ** 2.)

# don't count the orbits of the outer solar system in finding figure limits
ns = np.where(usedkics != kicsolar)[0]

# this section manually makes the aspect ratio equal
#  but completely fills the figure

# need this much buffer zone so that planets don't get cut off
buffsx = (fullxcens[ns].max() - fullxcens[ns].min()) * 0.007
buffsy = (fullycens[ns].max() - fullycens[ns].min()) * 0.007
# current limits of the figure
xmax = (ell_cx[ns] + ell_hx[ns]).max() + buffsx
xmin = (ell_cx[ns] - ell_hx[ns]).min() - buffsx
ymax = (ell_cy[ns] + ell_hy[ns]).max() + buffsy
ymin = (ell_cy[ns] - ell_hy[ns]).min() - buffsy

# figure aspect ratio
sr = 16. / 9.

# make the aspect ratio exactly right
if (xmax - xmin) / (ymax - ymin) > sr:
    plt.xlim(xmin, xmax)
    plt.ylim((ymax + ymin) / 2. - (xmax - xmin) / (2. * sr),
             (ymax + ymin) / 2. + (xmax - xmin) / (2. * sr))
else:
    plt.ylim(ymin, ymax)
    plt.xlim((xmax + xmin) / 2. - (ymax - ymin) * sr / 2.,
             (xmax + xmin) / 2. + (ymax - ymin) * sr / 2.)

lws = {480: 1, 720: 1, 1080: 2}
sslws = {480: 2, 720: 2, 1080: 4}
# Solar System orbits are dashed. Matplotlib sizes dashes in screen points,
# so while the camera zooms the circumference grows but the dashes don't:
# dashes get added/removed and slide around the circle, which looks like the
# orbit is rotating. Instead, each dashed orbit keeps a fixed number of
# dashes and their length is rescaled with the zoom every frame.
ss_orbits = []
fig_width_pts = fig.get_size_inches()[0] * 72.
xdiff_full = np.diff(plt.xlim())[0] / 2.
# matplotlib's default dashed pattern, in units of the line width
dash_on, dash_off = 3.7, 1.6


def update_dashes(zoom):
    """Rescale Solar System dashes so their count stays fixed."""
    # points per AU at this zoom level
    ppu = fig_width_pts / (2. * xdiff_full * zoom)
    for art, a, lw, ndash in ss_orbits:
        period = 2. * np.pi * a * ppu / ndash  # one dash + gap, in points
        frac = dash_on / (dash_on + dash_off)
        scale = lw if plt.rcParams['lines.scale_dashes'] else 1.
        art.set_linestyle((0, (period * frac / scale,
                               period * (1. - frac) / scale)))


# plot the orbital circles for every planet
for ii in np.arange(len(t0s)):
    # solid, thinner lines for normal planets
    ls = 'solid'
    zo = 0
    lw = lws[reso]
    # dashed, thicker ones for the solar system
    if usedkics[ii] == kicsolar:
        ls = 'dashed'
        zo = -3
        lw = sslws[reso]

    # ellipse with the star at one focus: the center is offset from the star
    # by a*e, opposite the periastron direction (theta = -f_tr)
    peri = -f_tr[ii]
    a = semis[ii]
    e = eccs[ii]
    c = Ellipse((fullxcens[ii] - a * e * np.cos(peri),
                 fullycens[ii] - a * e * np.sin(peri)),
                width=2. * a, height=2. * a * np.sqrt(1. - e ** 2.),
                angle=np.degrees(peri), clip_on=False,
                alpha=orbitalpha, fill=False,
                color=orbitcol, zorder=zo, ls=ls, lw=lw)
    fig.gca().add_artist(c)
    if usedkics[ii] == kicsolar:
        # number of dashes that looks like the default style at full zoom
        ppu = fig_width_pts / (2. * xdiff_full)
        ndash = 2. * np.pi * a * ppu / ((dash_on + dash_off) * lw)
        ss_orbits.append((c, a, lw, max(int(round(ndash)), 12)))
update_dashes(1.)

# set up the planet size scale
sscales = {480: 12., 720: 30., 1080: 50.}
sscale = sscales[reso]

rearth = 1.
rnep = 3.856
rjup = 10.864
rmerc = 0.383
# for the planet size legend
solarsys = np.array([rmerc, rearth, rnep, rjup])
pnames = ['Mercury', 'Earth', 'Neptune', 'Jupiter']
csolar = np.array([409, 255, 46, 112])

# keep the smallest planets visible and the largest from being too huge
solarsys = np.clip(solarsys, 0.8, 1.3 * rjup)
solarscale = sscale * solarsys

radii = np.clip(radii, 0.8, 1.3 * rjup)
pscale = sscale * radii

# color bar temperature tick values and labels
ticks = np.array([250, 500, 750, 1000, 1250])
labs = ['250', '500', '750', '1000', '1250']

# blue and red colors for the color bar
RGB1 = np.array([1, 185, 252])
RGB2 = np.array([220, 55, 19])

# create the diverging map with a white in the center
mycmap = diverge_map(RGB1=RGB1, RGB2=RGB2, numColors=15)

# just plot the planets at time 0. for this default plot
px, py = planet_xy(times[0])
tmp = plt.scatter(px, py, marker='o',
                  edgecolors='none', lw=0, s=pscale, c=teqs, vmin=ticks.min(),
                  vmax=ticks.max(), zorder=3, cmap=mycmap, clip_on=False)

fsz1 = fszs1[reso]
fsz2 = fszs2[reso]
prop = fm.FontProperties(fname=fontfile)

# create the 'Solar System' text identification
if addsolar:
    loc = np.where(usedkics == kicsolar)[0][0]
    plt.text(fullxcens[loc], fullycens[loc], 'Solar\nSystem', zorder=-2,
             color=fontcol, family=fontfam, fontproperties=prop, fontsize=fsz1,
             horizontalalignment='center', verticalalignment='center')

# if we're putting in a translucent background behind the text
# to make it easier to read
if legback:
    box1starts = {480: (0., 0.445), 720: (0., 0.46), 1080: (0., 0.47)}
    box1widths = {480: 0.19, 720: 0.147, 1080: 0.153}
    box1heights = {480: 0.555, 720: 0.54, 1080: 0.53}

    box2starts = {480: (0.79, 0.8), 720: (0.83, 0.84), 1080: (0.83, 0.84)}
    box2widths = {480: 0.21, 720: 0.17, 1080: 0.17}
    box2heights = {480: 0.2, 720: 0.16, 1080: 0.16}

    # create the rectangles at the right heights and widths
    # based on the resolution
    c = plt.Rectangle(box1starts[reso], box1widths[reso], box1heights[reso],
                      alpha=legalpha, fc=legbackcol, ec='none', zorder=4,
                      transform=ax.transAxes)
    d = plt.Rectangle(box2starts[reso], box2widths[reso], box2heights[reso],
                      alpha=legalpha, fc=legbackcol, ec='none', zorder=4,
                      transform=ax.transAxes)
    ax.add_artist(c)
    ax.add_artist(d)

# appropriate spacing from the left edge for the color bar
cbxoffs = {480: 0.09, 720: 0.07, 1080: 0.074}
cbxoff = cbxoffs[reso]

# plot the solar system planet scale
ax.scatter(np.zeros(len(solarscale)) + cbxoff,
           1. - 0.13 + 0.03 * np.arange(len(solarscale)), s=solarscale,
           c=csolar, zorder=5, marker='o',
           edgecolors='none', lw=0, cmap=mycmap, vmin=ticks.min(),
           vmax=ticks.max(), clip_on=False, transform=ax.transAxes)

# put in the text labels for the solar system planet scale
for ii in np.arange(len(solarscale)):
    ax.text(cbxoff + 0.01, 1. - 0.14 + 0.03 * ii,
            pnames[ii], color=fontcol, family=fontfam,
            fontproperties=prop, fontsize=fsz1, zorder=5,
            transform=ax.transAxes)

# colorbar axis on the left centered with the planet scale
ax2 = fig.add_axes([cbxoff - 0.005, 0.54, 0.01, 0.3])
ax2.set_zorder(2)
cbar = plt.colorbar(tmp, cax=ax2, extend='both', ticks=ticks)
# remove the white/black outline around the color bar
cbar.outline.set_linewidth(0)
# allow two different tick scales
cbar.ax.minorticks_on()
# turn off tick lines and put the physical temperature scale on the left
cbar.ax.tick_params(axis='y', which='major', color=fontcol, width=2,
                    left=False, right=False, length=5, labelleft=True,
                    labelright=False, zorder=5)
# turn off tick lines and put the physical temperature approximations
# on the right
cbar.ax.tick_params(axis='y', which='minor', color=fontcol, width=2,
                    left=False, right=False, length=5, labelleft=False,
                    labelright=True, zorder=5)
# say where to put the physical temperature approximations and give them labels
cbar.ax.yaxis.set_ticks([255, 409, 730, 1200], minor=True)
cbar.ax.set_yticklabels(labs, color=fontcol, family=fontfam,
                        fontproperties=prop, fontsize=fsz1, zorder=5)
cbar.ax.set_yticklabels(['Earth', 'Mercury', 'Surface\nof Venus', 'Lava'],
                        minor=True, color=fontcol, family=fontfam,
                        fontproperties=prop, fontsize=fsz1)
clab = 'Planet Equilibrium\nTemperature (K)'
# add the overall label at the bottom of the color bar
# labelpad (points) moves it down, clear of the bottom tick labels
clabpads = {480: 6, 720: 8, 1080: 16}
cbar.ax.set_xlabel(clab, color=fontcol, family=fontfam, fontproperties=prop,
                   size=fsz1, zorder=5, labelpad=clabpads[reso],
                   linespacing=1.3)

# switch back to the main plot
plt.sca(ax)

# upper right credit and labels text offsets
txtxoffs = {480: 0.2, 720: 0.16, 1080: 0.16}
txtyoffs1 = {480: 0.10, 720: 0.08, 1080: 0.08}
txtyoffs2 = {480: 0.18, 720: 0.144, 1080: 0.144}

txtxoff = txtxoffs[reso]
txtyoff1 = txtyoffs1[reso]
txtyoff2 = txtyoffs2[reso]

# put in the credits in the top right
text = plt.text(1. - txtxoff, 1. - txtyoff1,
                'TESS Orrery\nDay 0', color=fontcol,
                family=fontfam, fontproperties=prop,
                fontsize=fsz2, zorder=5, transform=ax.transAxes)
plt.text(1. - txtxoff, 1. - txtyoff2, 'After Ethan Kruse\'s\nOrrery',
         color=fontcol, family=fontfam,
         fontproperties=prop, fontsize=fsz1,
         zorder=5, transform=ax.transAxes)

# the center of the figure
x0 = np.mean(plt.xlim())
y0 = np.mean(plt.ylim())

# width of the figure
xdiff = np.diff(plt.xlim()) / 2.
ydiff = np.diff(plt.ylim()) / 2.

# set up the camera path now that the field's center and size are known
inds = np.arange(len(times))
nmax = max(inds[-1], 1)
zooms = np.zeros_like(times) - 1.
x0s = np.zeros_like(times) + np.nan
y0s = np.zeros_like(times) + np.nan
startx, starty = (ssx, ssy) if (addsolar and fixedpos) else (x0, y0)
if endx is None:
    endx, endy = 2. * x0 - startx, 2. * y0 - starty
# zoomed in at the start
zooms[inds < 0.25 * nmax] = zoom_in
x0s[inds < 0.25 * nmax] = startx
y0s[inds < 0.25 * nmax] = starty
# whole field, centered, in the middle
mid = (inds > 0.5 * nmax) & (inds < 0.6 * nmax)
zooms[mid] = 1.
x0s[mid] = x0
y0s[mid] = y0
# zoomed in again at the end
zooms[inds > 0.85 * nmax] = zoom_in
x0s[inds > 0.85 * nmax] = endx
y0s[inds > 0.85 * nmax] = endy
zooms[zooms < 0.] = np.nan
for arr in (zooms, x0s, y0s):
    unset = ~np.isfinite(arr)
    if unset.any() and (~unset).any():
        arr[unset] = np.interp(inds[unset], inds[~unset], arr[~unset])

# create the output directory if necessary
if makemovie and not os.path.exists(outdir):
    os.mkdir(outdir)

if makemovie:
    # get rid of all old png files so they don't get included in a new movie
    oldfiles = glob(os.path.join(outdir, '*png'))
    for delfile in oldfiles:
        os.remove(delfile)

    # go through all the times and make the planets move
    for ii, time in enumerate(times):
        # remove old planet locations and dates
        tmp.remove()
        text.remove()

        # re-zoom to appropriate level
        plt.xlim([x0s[ii] - xdiff * zooms[ii], x0s[ii] + xdiff * zooms[ii]])
        plt.ylim([y0s[ii] - ydiff * zooms[ii], y0s[ii] + ydiff * zooms[ii]])
        update_dashes(zooms[ii])

        # elapsed time since the start of the movie
        text = plt.text(1. - txtxoff, 1. - txtyoff1,
                        'TESS Orrery\nDay {0:.0f}'.format(time - times[0]),
                        color=fontcol, family=fontfam,
                        fontproperties=prop,
                        fontsize=fsz2, zorder=5, transform=ax.transAxes)
        # put the planets in the correct location
        px, py = planet_xy(time)
        tmp = plt.scatter(px, py,
                          marker='o', edgecolors='none', lw=0, s=pscale, c=teqs,
                          vmin=ticks.min(), vmax=ticks.max(),
                          zorder=3, cmap=mycmap, clip_on=False)

        fig.savefig(os.path.join(outdir, 'fig{0:04d}.png'.format(ii)),
                    facecolor=fig.get_facecolor(), edgecolor='none')
        if not (ii % 10):
            print('{0} of {1} frames'.format(ii, len(times)))
