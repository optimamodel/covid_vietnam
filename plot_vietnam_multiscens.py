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
import seaborn as sns

# Filepaths
figsfolder = 'figs234'
resfolder = 'results'
simsfilepath = f'{resfolder}/vietnam_sim.obj'
borders_open = '2020-12-01'

T = sc.tic()
thresholds = np.arange(10,60,10)
# Import files
filepaths = [f'{resfolder}/vietnam_sim_{t}.obj' for t in thresholds]
sims = []
for fp in filepaths:
    simsfile = sc.loadobj(fp)
    sims.append(simsfile.sims)
sim = sims[0][0] # Extract a sim to refer to

borders_open_ind = sim.day(borders_open)
cuminf = []
newdiag = []
for tn,t in enumerate(thresholds):
    cuminf.append([s.results['cum_infections'].values[-1] - s.results['cum_infections'].values[borders_open_ind] for s in sims[tn]])
    newdiag.append([s.results['new_diagnoses'].values[borders_open_ind-14:] for s in sims[tn]])


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
ygapt = 0.075
nrows = 1
ncols = 2
dx = (1 - (ncols - 1) * xgapm - xgapl - xgapr) / ncols
dy = (1 - (nrows - 1) * ygapm - ygapb - ygapt) / nrows
nplots = nrows * ncols
ax = {}

pl.figtext(xgapl*0.5,           ygapb + dy, 'A', fontweight='bold', fontsize=45)
pl.figtext(xgapl*0.5+xgapm+dx,  ygapb + dy, 'B', fontweight='bold', fontsize=45)

# Set up a dataframe for seaborn plotting
labels = [f'{t}%' for t in thresholds]
df = pd.DataFrame(np.array(cuminf).T, columns=labels)
df2 = df.melt()

for pn in range(nplots):
    ax[pn] = pl.axes([xgapl + (dx + xgapm) * (pn % ncols), ygapb + (ygapm + dy) * (pn // ncols), dx, dy])

    if pn==0:
        for tn, t in enumerate(thresholds):
            yarr = np.array(newdiag[tn])
            best = pl.median(yarr, axis=0)
            smoothed = [best[i-14:i].sum()/14 for i in range(14,len(best))]
            ax[pn].plot(np.arange(len(best)-14), smoothed, lw=4, alpha=1.0, label=f'{t}% testing')
            pl.legend(loc='upper left', frameon=False, fontsize=36)
            ax[pn].set_ylabel('Daily diagnoses (14 day trailing average)')

        @ticker.FuncFormatter
        def date_formatter(x, pos):
            return (cv.date('2020-11-15') + dt.timedelta(days=x)).strftime('%b-%y')

        ax[pn].xaxis.set_major_formatter(date_formatter)

        datemarks = pl.array([sim.day('2020-12-01'), sim.day('2021-01-01'), sim.day('2021-02-01'), sim.day('2021-03-01')]) * 1. - sim.day('2020-11-30')
        ax[pn].set_xticks(datemarks)

    if pn==1:
        ax[pn] = sns.swarmplot(x="variable", y="value", data=df2, color="grey", alpha=0.5)
        ax[pn] = sns.violinplot(x="variable", y="value", data=df2, color ="lightblue", alpha=0.5, inner=None)
        ax[pn] = sns.pointplot(x="variable", y="value", data=df2, ci=None, color ="steelblue", markers='D', scale = 1.2)

        ax[pn].set_ylabel('Cumulative infections, 1 Dec 2020 - 1 Mar 2021')
        ax[pn].set_xlabel('Symptomatic testing rate')

cv.savefig(f'{figsfolder}/fig4_multiscens.pdf')

print([np.median(cuminf[tn]) for tn in range(len(thresholds))])
print([np.quantile(cuminf[tn],q=0.025) for tn in range(len(thresholds))])
print([np.quantile(cuminf[tn],q=0.975) for tn in range(len(thresholds))])
sc.toc(T)