import covasim as cv
import pandas as pd
import sciris as sc
import pylab as pl
import numpy as np
from matplotlib import ticker
import datetime as dt
import matplotlib.patches as patches

# Filepaths
figsfolder = 'figs'
simsfilepath = 'vietnam_sim.obj'
today = '2020-10-05'

T = sc.tic()

# Import files
simsfile = sc.loadobj(simsfilepath)

# Define plotting functions
#%% Helper functions

def format_ax(ax, sim, key=None):
    @ticker.FuncFormatter
    def date_formatter(x, pos):
        return (sim['start_day'] + dt.timedelta(days=x)).strftime('%b-%y')
    ax.xaxis.set_major_formatter(date_formatter)
    pl.xlim([0, sim.day(today)])
    sc.boxoff()
    return

def plotter(key, sims, ax, ys=None, calib=False, label='', ylabel='', low_q=0.025, high_q=0.975, flabel=True, startday=None, subsample=2, chooseseed=None):

    which = key.split('_')[1]
    try:
        color = cv.get_colors()[which]
    except:
        color = [0.5,0.5,0.5]
    if which == 'diagnoses':
        color = [0.03137255, 0.37401   , 0.63813918, 1.        ]
    elif which == '':
        color = [0.82400815, 0.        , 0.        , 1.        ]

    if ys is None:
        ys = []
        for s in sims:
            ys.append(s.results[key].values)

    yarr = np.array(ys)
    if chooseseed is not None:
        best = sims[chooseseed].results[key].values
    else:
        best = pl.median(yarr, axis=0)
    low  = pl.quantile(yarr, q=low_q, axis=0)
    high = pl.quantile(yarr, q=high_q, axis=0)

    sim = sims[0] # For having a sim to refer to

    tvec = np.arange(len(best))
    if key in sim.data:
        data_t = np.array((sim.data.index-sim['start_day'])/np.timedelta64(1,'D'))
        inds = np.arange(0, len(data_t), subsample)
        pl.plot(data_t[inds], sim.data[key][inds], 'd', c=color, markersize=15, alpha=0.75, label='Data')

    start = None
    if startday is not None:
        start = sim.day(startday)
    end = sim.day(today)
    if flabel:
        if which == 'infections':
            fill_label = '95% projected interval'
        else:
            fill_label = '95% projected interval'
    else:
        fill_label = None
    pl.fill_between(tvec[startday:end], low[startday:end], high[startday:end], facecolor=color, alpha=0.2, label=fill_label)
    pl.plot(tvec[startday:end], best[startday:end], c=color, label=label, lw=4, alpha=1.0)

    if key == 'cum_infections':
        print(f'Estimated {which} on July 25: {best[sim.day("2020-07-25")]} (95%: {low[sim.day("2020-07-25")]}-{high[sim.day("2020-07-25")]})')
        print(f'Estimated {which} overall: {best[sim.day(today)]} (95%: {low[sim.day(today)]}-{high[sim.day(today)]})')
    elif key=='n_infectious':
        peakday = sc.findinds(best,max(best))
        peakval = max(best)
        print(f'Estimated peak {which} on {sim.date(peakday[0])}: {peakval} (95%: {low[peakday]}-{high[peakday]})')

    sc.setylim()

    xmin,xmax = ax.get_xlim()
    if calib:
        ax.set_xticks(pl.arange(xmin+2, xmax, 28))
    else:
        ax.set_xticks(pl.arange(xmin+2, xmax, 28))

    pl.ylabel(ylabel)
    datemarks = pl.array([sim.day('2020-07-01'), sim.day('2020-08-01'), sim.day('2020-09-01'), sim.day('2020-10-01')]) * 1.
    ax.set_xticks(datemarks)

    return


def plot_intervs(sim, labels=True):

    color = [0, 0, 0]
    jul25 = sim.day('2020-07-25')
    for day in [jul25, sim.day('2020-09-05'), sim.day('2020-09-14')]:
        pl.axvline(day, c=color, linestyle='--', alpha=0.4, lw=3)

    if labels:
        yl = pl.ylim()
        labely = yl[1]*0.85
        pl.text(jul25-17, labely, 'Danang\noutbreak', color=color, alpha=0.9, style='italic')
        pl.text(sim.day('2020-09-05')-15, labely, 'Work\nreopens', color=color, alpha=0.9, style='italic')
        pl.text(sim.day('2020-09-14') + 2, labely, 'School\nreopens', color=color, alpha=0.9, style='italic')
    return


# Fonts and sizes
font_size = 36
font_family = 'Libertinus Sans'
pl.rcParams['font.size'] = font_size
pl.rcParams['font.family'] = font_family
pl.figure(figsize=(24,16))

# Extract a sim to refer to
sims = simsfile.sims
sim = sims[0]

# Plot locations
ygapb = 0.05
ygapm = 0.05
ygapt = 0.01
xgapl = 0.065
xgapm = 0.05
xgapr = 0.02
remainingy = 1-(ygapb+ygapm+ygapt)
remainingx = 1-(xgapl+xgapm+xgapr)
dy = remainingy/2
dx1 = 0.5
dx2 = 1-dx1-(xgapl+xgapm+xgapr)
ax = {}

# a: daily diagnoses
ax[0] = pl.axes([xgapl, ygapb+ygapm+dy, dx1, dy])
format_ax(ax[0], sim)
plotter('new_diagnoses', sims, ax[0], calib=True, label='Model', ylabel='Daily diagnoses')
plot_intervs(sim)

# b. cumulative diagnoses
ax[1] = pl.axes([xgapl+xgapm+dx1, ygapb+ygapm+dy, dx2, dy])
format_ax(ax[1], sim)
plotter('cum_diagnoses', sims, ax[1], calib=True, label='Diagnoses\n(modelled)', ylabel='Cumulative diagnoses', flabel=False)
pl.legend(loc='upper left', frameon=False)
#pl.ylim([0, 10e3])

# c. cumulative and active infections
ax[2] = pl.axes([xgapl, ygapb, dx1, dy])
format_ax(ax[2], sim)
plotter('cum_infections', sims, ax[2], calib=True, label='Cumulative infections (modelled)', ylabel='', flabel=False)
plotter('n_infectious', sims, ax[2], calib=True, label='Active infections (modelled)', ylabel='Estimated infections', flabel=False)
pl.legend(loc='upper left', frameon=False)

# d. cumulative deaths
ax[3] = pl.axes([xgapl+xgapm+dx1, ygapb, dx2, dy])
format_ax(ax[3], sim)
plotter('cum_deaths', sims, ax[3], calib=True, label='Deaths\n(modelled)', ylabel='Cumulative deaths', flabel=False)
pl.legend(loc='upper left', frameon=False)
#pl.ylim([0, 10e3])

cv.savefig(f'fig1_calibration.png', dpi=100)

sc.toc(T)