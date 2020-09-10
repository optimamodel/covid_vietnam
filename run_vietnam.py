'''
Run Vietnam
'''

import covasim as cv
import sciris as sc
import pylab as pl

def make_sim():

    start_day = '2020-06-15'
    end_day = '2020-09-30'
    total_pop = 11.9e6 # Population of central Vietnam
    n_agents = 100e3
    pop_scale = total_pop/n_agents

    # Calibration parameters
    pars = {'pop_size': n_agents,
            'pop_infected': 15,
            'pop_scale': pop_scale,
            'rand_seed': 1,
            'beta': 0.0117,
            'start_day': start_day,
            'end_day': end_day,
            'verbose': .1,
            'rescale': True,
            'iso_factor': dict(h=0.5, s=0.01, w=0.01, c=0.1),  # Multiply beta by this factor for people in isolation
            'quar_factor': dict(h=1.0, s=0.2, w=0.2, c=0.2),   # Multiply beta by this factor for people in quarantine
            'location': 'vietnam',
            'pop_type': 'hybrid',
            'age_imports': [50,80],
            'rel_crit_prob': 3., # Calibration parameter due to hospital outbreak
            'rel_death_prob': 4., # Calibration parameter due to hospital outbreak
            }

    # Make a sim without parameters, just to load in the data to use in the testing intervention and to get the sim days
    sim = cv.Sim(start_day=start_day, datafile="vietnam_data.csv")

    pars['dur_imports'] = sc.dcp(sim.pars['dur'])
    pars['dur_imports']['exp2inf']  = {'dist':'lognormal_int', 'par1':0.0, 'par2':0.0}
    pars['dur_imports']['inf2sym']  = {'dist':'lognormal_int', 'par1':0.0, 'par2':0.0}
    pars['dur_imports']['sym2sev']  = {'dist':'lognormal_int', 'par1':0.0, 'par2':2.0}
    pars['dur_imports']['sev2crit'] = {'dist':'lognormal_int', 'par1':1.0, 'par2':3.0}
    pars['dur_imports']['crit2die'] = {'dist':'lognormal_int', 'par1':3.0, 'par2':3.0}

    # Add testing and tracing interventions
    trace_probs = {'h': 1, 's': 0.95, 'w': 0.8, 'c': 0.05}
    trace_time  = {'h': 0, 's': 2, 'w': 2, 'c': 5}
    pars['interventions'] = [
        cv.test_num(daily_tests=sim.data['new_tests'], start_day=sim.day('2020-07-01'), end_day=sim.day('2020-08-22'), symp_test=2.0, quar_test=1.0, do_plot=False),
        cv.test_num(daily_tests=7000, start_day=sim.day('2020-08-23'), symp_test=2.0, quar_test=1.0, do_plot=False),
        cv.contact_tracing(start_day=0, trace_probs=trace_probs, trace_time=trace_time, do_plot=False),
        cv.dynamic_pars({'n_imports': {'days': [sim.day('2020-07-20'), sim.day('2020-07-25')], 'vals': [10, 0]}}, do_plot=False),
        cv.change_beta(days=0, changes=0.4, trigger=cv.trigger('date_diagnosed',5))
        ]

    sim = cv.Sim(pars=pars, datafile="vietnam_data.csv")
    sim.initialize()

    return sim


# Run

T = sc.tic()
cv.check_save_version()

# Settings
domulti = True
doplot = True
dosave = False

# Plot settings
to_plot = sc.objdict({
    'Cumulative diagnoses': ['cum_diagnoses'],
    'Cumulative infections': ['cum_infections'],
    'New infections': ['new_infections'],
    'Daily diagnoses': ['new_diagnoses'],
    'Cumulative deaths': ['cum_deaths'],
    'Daily deaths': ['new_deaths'],
    'Cumulative tests': ['cum_tests'],
    'Daily tests': ['new_tests'],
    'Test yield': ['test_yield'],
    'Number quarantined': ['n_quarantined'],
    })

# Run and plot
sim = make_sim()
if domulti:
    msim = cv.MultiSim(base_sim=sim)
    msim.run(n_runs=10, reseed=True, noise=0)
    msim.reduce()
else: sim.run()

if dosave:
    if domulti: msim.save('vietnam.sim', keep_people=True)
    else: sim.save('vietnam.sim', keep_people=True)
if doplot:
    if domulti:
        msim.plot(to_plot=to_plot, n_cols=2, do_save=True, do_show=False, fig_path=f'vietnam.png',
                 legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)
    else:
        sim.plot(to_plot=to_plot, n_cols=2, do_save=True, do_show=False, fig_path=f'vietnam.png',
                 legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)


sc.toc(T)

pl.show()

