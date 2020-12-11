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
import matplotlib.ticker as mtick

# Filepaths
figsfolder = 'figs234'
resfolder = 'resultstest'
simsfilepath = f'{resfolder}/vietnam_sim.obj'
today = '2020-12-01'

T = sc.tic()
thresholds = np.array([0.01048074, 0.02206723, 0.0350389 , 0.04979978, 0.06696701])
# Import files
filepaths = [f'{resfolder}/vietnam_sim_{t}.obj' for t in thresholds]
sims = []
for fp in filepaths:
    simsfile = sc.loadobj(fp)
    sims.append(simsfile.sims)
sim = sims[0][0] # Extract a sim to refer to

todayind = sim.day(today)
cuminf = []
newdiag = []
for tn,t in enumerate(thresholds):
    cuminf.append([s.results['cum_infections'].values[-1] - s.results['cum_infections'].values[todayind] for s in sims[tn]])
    newdiag.append([s.results['new_diagnoses'].values[todayind-14:] for s in sims[tn]])


# Fonts and sizes
font_size = 36
font_family = 'Libertinus Sans'
pl.rcParams['font.size'] = font_size
pl.rcParams['font.family'] = font_family
pl.figure(figsize=(24,12))

# Plot locations
# Subplot sizes
xgapl = 0.067
xgapm = 0.1
xgapr = 0.015
ygapb = 0.1
ygapm = 0.02
ygapt = 0.06
nrows = 1
ncols = 2
dx = (1 - (ncols - 1) * xgapm - xgapl - xgapr) / ncols
dy = (1 - (nrows - 1) * ygapm - ygapb - ygapt) / nrows
nplots = nrows * ncols
ax = {}

for pn in range(nplots):
    ax[pn] = pl.axes([xgapl + (dx + xgapm) * (pn % ncols), ygapb + (ygapm + dy) * (pn // ncols), dx, dy])

    if pn==0:
        for tn, t in enumerate(thresholds):
            yarr = np.array(newdiag[tn])
            best = pl.median(yarr, axis=0)
            smoothed = [best[i-14:i].sum()/14 for i in range(14,len(best))]
            ax[pn].plot(np.arange(len(best)-14), smoothed, lw=4, alpha=1.0, label=f'{(tn+1)*10}% testing')
            pl.legend(loc='upper left', frameon=False, fontsize=36)
            ax[pn].set_ylabel('Daily diagnoses (14 day trailing average)')

        @ticker.FuncFormatter
        def date_formatter(x, pos):
            return (cv.date('2020-11-15') + dt.timedelta(days=x)).strftime('%b-%y')

        ax[pn].xaxis.set_major_formatter(date_formatter)

        datemarks = pl.array([sim.day('2020-12-01'), sim.day('2021-01-01'), sim.day('2021-02-01'), sim.day('2021-03-01')]) * 1. - sim.day('2020-11-30')
        ax[pn].set_xticks(datemarks)

    if pn==1:
        for tn, t in enumerate(thresholds):
            ax[pn].scatter([(tn+1)*10]*len(cuminf[tn]), cuminf[tn], s=400, c = [[0.4, 0.4, 0.4]], edgecolor='w')
            ax[pn].scatter([(tn+1)*10], [np.median(cuminf[tn])], s=400, c = [[1., 0.8, 0.86]], edgecolor='w')
        ax[pn].plot([(tn+1)*10 for tn in range(len(thresholds))], [np.median(cuminf[tn]) for tn in range(len(thresholds))], '-', c = [1., 0.8, 0.86], lw=4)
        ax[pn].set_ylabel('Cumulative infections, 1 Dec 2020 - 1 May 2021')
        ax[pn].set_xlabel('Symptomatic testing rate')
        ax[pn].xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))

cv.savefig(f'{figsfolder}/fig4_multiscens.png', dpi=100)

sc.toc(T)