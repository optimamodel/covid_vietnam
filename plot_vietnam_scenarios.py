import covasim as cv
import pandas as pd
import sciris as sc
import pylab as pl
import numpy as np
from matplotlib import ticker
import datetime as dt
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

# Filepaths
figsfolder = 'figs234'
resfolder = 'resultstest'
simsfilepath = f'{resfolder}/vietnam_sim.obj'
today = '2020-12-01'

T = sc.tic()

# Define plotting functions
#%% Helper functions

def format_ax(ax, sim, key=None):
    @ticker.FuncFormatter
    def date_formatter(x, pos):
        return (sim['start_day'] + dt.timedelta(days=x)).strftime('%b-%y')
    ax.xaxis.set_major_formatter(date_formatter)
    pl.xlim([0, sim['n_days']-30])
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
        pl.plot(data_t[inds], sim.data[key][inds], 'd', c=color, markersize=10, alpha=0.5, label='Data')

    start = None
    if startday is not None:
        start = sim.day(startday)
    end = sim.day('2021-03-31')
    if flabel:
        if which == 'infections':
            fill_label = '95% projected interval'
        else:
            fill_label = '95% projected interval'
    else:
        fill_label = None
    pl.fill_between(tvec[startday:end], low[startday:end], high[startday:end], facecolor=color, alpha=0.2, label=fill_label)
    pl.plot(tvec[startday:end], best[startday:end], c=color, label=label, lw=4, alpha=1.0)
    #for s in sims:
    #    pl.plot(tvec[startday:end], s.results[key].values[startday:end], c=[0.4, 0.4, 0.4], label=label, lw=1, alpha=0.7)

    #sc.setylim()

    datemarks = pl.array([sim.day('2020-07-01'),sim.day('2020-09-01'),sim.day('2020-11-01'),sim.day('2021-01-01'),sim.day('2021-03-01')])*1.
    ax.set_xticks(datemarks)

    pl.ylabel(ylabel)

    return


# Fonts and sizes
font_size = 36
font_family = 'Libertinus Sans'
pl.rcParams['font.size'] = font_size
pl.rcParams['font.family'] = font_family
pl.figure(figsize=(24,16))

# Plot locations
# Subplot sizes
xgapl = 0.067
xgapm = 0.02
xgapr = 0.015
ygapb = 0.05
ygapm = 0.02
ygapt = 0.06
nrows = 2
ncols = 3
dx = (1 - (ncols - 1) * xgapm - xgapl - xgapr) / ncols
dy = (1 - (nrows - 1) * ygapm - ygapb - ygapt) / nrows
nplots = nrows * ncols
ax = {}


# Import files
filepaths = [f'{resfolder}/vietnam_sim_{policy}.obj' for policy in ['remain','drop','dynamic']]
sims = []
for fp in filepaths:
    simsfile = sc.loadobj(fp)
    sims.append(simsfile.sims)
sim = sims[0][0] # Extract a sim to refer to

colors = [[0.03137255, 0.37401   , 0.63813918, 1.        ], '#c75649']
linecolor = [0, 0, 0]
importday = sim.day('2020-12-01')

# Add text
headings =["    Constant high compliance   ",
           "            Increased apathy             ",
           "      Self-regulating behavior     "]
epsx = 0.003
epsy = 0.008
llpad = 0.01
rlpad = 0.005

for nc in range(ncols):
    pl.figtext(xgapl + (dx + xgapm) * nc + epsx, ygapb + dy * nrows + ygapm * (nrows - 1) + llpad, headings[nc],
           fontsize=36, fontweight='bold', bbox={'edgecolor': 'none', 'facecolor': 'silver', 'alpha': 0.5, 'pad': 4})


for pn in range(nplots):
    ax[pn] = pl.axes([xgapl + (dx + xgapm) * (pn % ncols), ygapb + (ygapm + dy) * (pn // ncols), dx, dy])
    format_ax(ax[pn], sim)
    ax[pn].axvline(importday, c=linecolor, linestyle='--', alpha=0.4, lw=3)

    if pn in range(ncols):
        plotter('new_diagnoses', sims[(pn%ncols)], ax[pn])
        ax[pn].set_ylim(0, 150)
        ax[pn].set_yticks(np.arange(0, 150, 25))
        ax[pn].grid(linestyle=':', linewidth='0.5', color='grey', axis='y')
#        plt.grid(color='black', which='major', axis='y', linestyle='solid')
    else:
        plotter('n_exposed', sims[(pn%ncols)], ax[pn])
        ax[pn].set_xticklabels([])
        ax[pn].set_ylim(0, 3000)
        ax[pn].set_yticks(np.arange(0, 3000, 500))
        ax[pn].grid(linestyle=':', linewidth='0.5', color='grey', axis='y')

    if (pn%ncols) != 0:
        ax[pn].set_yticklabels([])
    else:
        ax[pn].set_ylabel('Daily diagnoses') if pn == 0 else ax[pn].set_ylabel('Active infections')

cv.savefig(f'{figsfolder}/fig3_scenarios.png', dpi=100)


sc.toc(T)