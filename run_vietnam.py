import covasim as cv
import pandas as pd
import sciris as sc
import numpy as np


def make_sim(beta=None, symp_prob=None, asymp_quar_prob=None):

    end_day = '2020-08-12'

    pars = {'pop_size': 100e3,
            'pop_infected': 100,
            'rand_seed': 111,
            'beta': beta,
            'start_day': '2020-07-20',
            'end_day': end_day,
            'verbose': .1,
            'location': 'vietnam',
            'pop_type': 'hybrid'}

    # Testing and tracing
    trace_probs = {'h': 1, 's': 0.95, 'w': 0.8, 'c': 0.2}
    trace_time  = {'h': 0, 's': 2, 'w': 2, 'c': 14}
    pars['interventions'] = [cv.test_prob(start_day=0, symp_prob=symp_prob, asymp_quar_prob=asymp_quar_prob, do_plot=False),
                             cv.contact_tracing(start_day=0, trace_probs=trace_probs, trace_time=trace_time, do_plot=False)
                             ]

    sim = cv.Sim(pars=pars, datafile="vietnam_data.csv")

    sim.initialize()

    return sim


# Run

T = sc.tic()

# Settings
doplot = True
dosave = False

# Plot settings
to_plot = sc.objdict({
    'Cumulative diagnoses': ['cum_diagnoses'],
    'Cumulative infections': ['cum_infections'],
    'New infections': ['new_infections'],
    'Daily diagnoses': ['new_diagnoses'],
#    'Cumulative deaths': ['cum_deaths'],
#    'Daily deaths': ['new_deaths'],
    })

# Run and plot
sim = make_sim(beta=0.025, symp_prob=0.2, asymp_quar_prob=0.1)
sim.run()
if dosave: sim.save()
if doplot: sim.plot(to_plot=to_plot, n_cols=2, do_save=True, do_show=False, fig_path=f'vietnam.png',
                 legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=5)

sc.toc(T)