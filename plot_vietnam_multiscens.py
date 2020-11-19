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
figsfolder = 'figs'
today = '2020-11-15'

T = sc.tic()
thresholds = np.arange(10,50,10)
# Import files
filepaths = [f'vietnam_sim_{t}.obj' for t in thresholds] + [f'vietnam_sim_{t}.obj' for t in thresholds]
sims = []
for fp in filepaths:
    simsfile = sc.loadobj(fp)
    sims.append(simsfile.sims)
sim = sims[0][0] # Extract a sim to refer to

todayind = sim.day(today)
cumdiag = []
newinf = []
for tn,t in enumerate(thresholds):
    cumdiag.append([s.results['cum_infections'].values[-1] - s.results['cum_infections'].values[todayind] for s in sims[tn]])
    newinf.append([s.results['new_diagnoses'].values[todayind-14:] for s in sims[tn]])


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
            yarr = np.array(newinf[tn])
            best = pl.median(yarr, axis=0)
            #best = np.max(yarr, axis=0)
            smoothed = [best[i-14:i].sum()/14 for i in range(14,len(best))]
            ax[pn].plot(np.arange(len(best)-14), smoothed, lw=4, alpha=1.0, label=f'Adapt after {t} cases')
            pl.legend(loc='upper left', frameon=False, fontsize=36)
            ax[pn].set_ylabel('Daily infections (14 day trailing average)')

        @ticker.FuncFormatter
        def date_formatter(x, pos):
            return (cv.date('2020-11-15') + dt.timedelta(days=x)).strftime('%b-%d')

        ax[pn].xaxis.set_major_formatter(date_formatter)

    if pn==1:
        for tn, t in enumerate(thresholds):
            ax[pn].scatter([t]*len(cumdiag[tn]), cumdiag[tn], s=400, c = [[0.4, 0.4, 0.4]], edgecolor='w')
            ax[pn].scatter([t], [np.median(cumdiag[tn])], s=400, c = [[1., 0.8, 0.86]], edgecolor='w')
        ax[pn].plot(thresholds, [np.median(cumdiag[tn]) for tn in range(len(thresholds))], '-', c = [1., 0.8, 0.86], lw=4)
        ax[pn].set_ylabel('Cumulative diagnoses, 15 Nov 2020 - 1 Mar 2021')
        ax[pn].set_xlabel('Number of daily cases before behavior changes')

cv.savefig(f'fig3_multiscenss.png', dpi=100)

#n_lines=len(sims[0])
#x = np.arange(len(sim.results['new_diagnoses'].values))
#xs = np.array([x for i in range(n_lines)])

#for pn in [0,1,2]:
#    yval = np.array([s.results['new_diagnoses'].values[-1] for s in sims[pn]])
#    for s in sims[pn]:
#        ax[pn].plot(np.arange(len(s.results['new_diagnoses'].values)), s.results['new_diagnoses'].values, '-', lw=1, c=colors[0], alpha=1.0)
#        ax[pn].set_ylim(0, 400)
#    if (pn%ncols) != 0:
#        ax[pn].set_yticklabels([])
#ax[0].set_ylabel('Daily diagnoses')
#for pn in [3,4,5]:
#    for s in sims[pn-3]:
#        ax[pn].plot(np.arange(len(s.results['n_exposed'].values)), s.results['n_exposed'].values, '-', lw=1, c=colors[1], alpha=1.0)
#        ax[pn].set_ylim(0, 3000)
#    if (pn % ncols) != 0:
#        ax[pn].set_yticklabels([])
#    ax[pn].set_xticklabels([])
#ax[3].set_ylabel('Active infections')


#    if pn == nplots: pl.legend(loc='upper right', frameon=False, fontsize=20)


sc.toc(T)