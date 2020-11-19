'''
Run calibration for central Vietnam
'''

import covasim as cv
import sciris as sc
import pylab as pl
import numpy as np


# Make the sim
def make_sim(seed, beta, policy='remain', threshold=5, end_day=None):

    start_day = '2020-06-15'
    if end_day is None: end_day = '2021-02-28'
    total_pop = 11.9e6 #95.5e6 # Population of central Vietnam
    n_agents = 100e3
    pop_scale = total_pop/n_agents

    # Calibration parameters
    pars = {'pop_size': n_agents,
            'pop_infected': 10,
            'pop_scale': pop_scale,
            'rand_seed': seed,
            'beta': beta,#0.0145
            'start_day': start_day,
            'end_day': end_day,
            'verbose': 0,
            'rescale': True,
            'iso_factor': dict(h=0.5, s=0.01, w=0.01, c=0.1),  # Multiply beta by this factor for people in isolation
            'quar_factor': dict(h=1.0, s=0.2, w=0.2, c=0.2),   # Multiply beta by this factor for people in quarantine
            'location': 'vietnam',
            'pop_type': 'hybrid',
            'age_imports': [50,80],
            'rel_crit_prob': 1.5, # Calibration parameter due to hospital outbreak
            'rel_death_prob': 1.5, # Calibration parameter due to hospital outbreak
            }

    # Make a sim without parameters, just to load in the data to use in the testing intervention and to get the sim days
    sim = cv.Sim(start_day=start_day, datafile="vietnam_data.csv")

    # Set up import assumptions
    pars['dur_imports'] = sc.dcp(sim.pars['dur'])
    pars['dur_imports']['exp2inf']  = {'dist':'lognormal_int', 'par1':0.0, 'par2':0.0}
    pars['dur_imports']['inf2sym']  = {'dist':'lognormal_int', 'par1':0.0, 'par2':0.0}
    pars['dur_imports']['sym2sev']  = {'dist':'lognormal_int', 'par1':0.0, 'par2':2.0}
    pars['dur_imports']['sev2crit'] = {'dist':'lognormal_int', 'par1':1.0, 'par2':3.0}
    pars['dur_imports']['crit2die'] = {'dist':'lognormal_int', 'par1':3.0, 'par2':3.0}

    # Define import array
    import_start = sim.day('2020-07-20')
    import_end   = sim.day('2020-07-25')
    border_start = sim.day('2020-11-15')
    final_day_ind  = sim.day('2020-02-28')
    imports = np.concatenate((pl.zeros(import_start), # No imports until the import start day
                              pl.ones(import_end-import_start)*20, # 20 imports/day over the first importation window
                              pl.zeros(border_start-import_end), # No imports from the end of the 1st importation window to the border reopening
                              cv.n_neg_binomial(1, 0.5, final_day_ind-border_start) # Negative-binomial distributed importations each day
                              ))
    pars['n_imports'] = imports

    # Add testing and tracing interventions
    trace_probs = {'h': 1, 's': 0.95, 'w': 0.8, 'c': 0.05}
    trace_time  = {'h': 0, 's': 2, 'w': 2, 'c': 5}
    pars['interventions'] = [
        # Testing and tracing
        cv.test_num(daily_tests=sim.data['new_tests'], start_day=sim.day('2020-07-01'), end_day=sim.day('2020-08-22'), symp_test=100, quar_test=100, do_plot=False),
        cv.test_prob(start_day=sim.day('2020-08-23'), symp_prob=0.2, asymp_quar_prob=0.5, do_plot=False),
        cv.contact_tracing(start_day=0, trace_probs=trace_probs, trace_time=trace_time, do_plot=False),

        # Change death and critical probabilities
        cv.dynamic_pars({'rel_death_prob':{'days':sim.day('2020-08-31'), 'vals':1.0},'rel_crit_prob':{'days':sim.day('2020-08-31'), 'vals':1.0}},do_plot=False), # Assume these were elevated due to the hospital outbreak but then would return to normal

        # Increase precautions (especially mask usage) following the outbreak, which are then abandoned after 40 weeks of low case counts
        cv.change_beta(days=0, changes=[0.25], trigger=cv.trigger('date_diagnosed', 5)),

        # Close schools and workplaces
        cv.clip_edges(days=['2020-07-28', '2020-09-14'], changes=[0.1, 1.], layers=['s'], do_plot=True),
        cv.clip_edges(days=['2020-07-28', '2020-09-05'], changes=[0.5, 1.], layers=['w'], do_plot=False),
        ]

    if policy != 'remain':
        pars['interventions'] += [cv.change_beta(days=80, changes=[1.0], trigger=cv.trigger('date_diagnosed', 2, direction='below', smoothing=28))]
    if policy == 'dynamic':
        pars['interventions'] += [cv.change_beta(days=140, changes=[0.25], trigger=cv.trigger('date_diagnosed', threshold)),
                                  cv.clip_edges(days=[140], changes=[0.1], layers=['s'], trigger=cv.trigger('date_diagnosed', threshold)),
                                  cv.clip_edges(days=[140], changes=[0.5], layers=['w'], trigger=cv.trigger('date_diagnosed', threshold)),
                                  ]

    sim = cv.Sim(pars=pars, datafile="vietnam_data.csv")
    sim.initialize()

    return sim


T = sc.tic()
cv.check_save_version()

whattorun = ['quickfit', 'fitting', 'mainscens', 'multiscens'][1]
do_plot = True
do_save = True
save_sim = True
n_runs = 400
betas = [i / 10000 for i in range(135, 156, 1)]
today = '2020-10-15'

# Quick calibration
if whattorun=='quickfit':
    s0 = make_sim(seed=1, beta=0.0145, end_day=today)
    sims = []
    for seed in range(6):
        sim = s0.copy()
        sim['rand_seed'] = seed
        sim.set_seed()
        sims.append(sim)
    msim = cv.MultiSim(sims)
    msim.run()
    msim.reduce()
    # Plot settings
    to_plot = sc.objdict({
        'Cumulative diagnoses': ['cum_diagnoses'],
        'Cumulative infections': ['cum_infections'],
        'New infections': ['new_infections'],
        'Daily diagnoses': ['new_diagnoses'],
        'Cumulative deaths': ['cum_deaths'],
        'Daily deaths': ['new_deaths'],
        })

    msim.plot(to_plot=to_plot, do_save=True, do_show=False, fig_path=f'vietnam.png',
              legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)


# Iterate for calibration
elif whattorun=='fitting':
    fitsummary = {}
    fitsummary['allmismatches'] = []
    fitsummary['percentlt75'] = []
    fitsummary['percentlt100'] = []

    for beta in betas:
        s0 = make_sim(seed=1, beta=beta, end_day=today)
        sims = []
        for seed in range(n_runs):
            sim = s0.copy()
            sim['rand_seed'] = seed
            sim.set_seed()
            sims.append(sim)
        msim = cv.MultiSim(sims)
        msim.run()
        fitsummary['allmismatches'].append([sim.compute_fit().mismatch for sim in msim.sims])
        fitsummary['percentlt75'].append([i for i in range(n_runs) if fitsummary['allmismatches'][-1][i]<75])
        fitsummary['percentlt100'].append([i for i in range(n_runs) if fitsummary['allmismatches'][-1][i]<100])
    sc.saveobj(f'fitsummary.obj',fitsummary)


elif whattorun=='mainscens':
    # Load good seeds
    fitsummary = sc.loadobj('fitsummary.obj')
    #betas = [i / 10000 for i in range(140, 151, 1)]
    for policy in ['remain','drop','dynamic']:
        sims = []
        sc.blank()
        print('---------------\n')
        print(f'Starting {policy} policy runs... ')
        print('---------------\n')
        for bn,beta in enumerate(betas):
            s0 = make_sim(seed=1, beta=beta, policy=policy)
            goodseeds = [i for i in range(n_runs) if fitsummary['allmismatches'][bn][i] < 100]
            if len(goodseeds)>0:
                for seed in goodseeds:
                    sim = s0.copy()
                    sim['rand_seed'] = seed
                    sim.set_seed()
                    sims.append(sim)
        msim = cv.MultiSim(sims)
        msim.run()
        to_plot = sc.objdict({
            'Cumulative diagnoses': ['cum_diagnoses'],
            'Cumulative infections': ['cum_infections'],
            'New infections': ['new_infections'],
            'Daily diagnoses': ['new_diagnoses'],
            'Cumulative deaths': ['cum_deaths'],
            'Daily deaths': ['new_deaths'],
            })

        if save_sim:
            msim.save(f'vietnam_sim_{policy}.obj')
        if do_plot:
            msim.reduce()
            msim.plot(to_plot=to_plot, do_save=do_save, do_show=False, fig_path=f'vietnam_{policy}.png',
                      legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)


elif whattorun=='multiscens':
    # Load good seeds
    fitsummary = sc.loadobj('fitsummary.obj')
    thresholds = np.arange(10,60,10)
    for threshold in thresholds:
        sims = []
        sc.blank()
        print('---------------\n')
        print(f'Starting {threshold} policy runs... ')
        print('---------------\n')
        for bn,beta in enumerate(betas):
            s0 = make_sim(seed=1, beta=beta, policy='dynamic', threshold=threshold)
            goodseeds = [i for i in range(n_runs) if fitsummary['allmismatches'][bn][i] < 100]
            if len(goodseeds)>0:
                for seed in goodseeds:
                    sim = s0.copy()
                    sim['rand_seed'] = seed
                    sim.set_seed()
                    sims.append(sim)
        msim = cv.MultiSim(sims)
        msim.run()
        to_plot = sc.objdict({
            'Cumulative diagnoses': ['cum_diagnoses'],
            'Cumulative infections': ['cum_infections'],
            'New infections': ['new_infections'],
            'Daily diagnoses': ['new_diagnoses'],
            'Cumulative deaths': ['cum_deaths'],
            'Daily deaths': ['new_deaths'],
            })

        if save_sim:
            msim.save(f'vietnam_sim_{threshold}.obj')
        if do_plot:
            msim.reduce()
            msim.plot(to_plot=to_plot, do_save=do_save, do_show=False, fig_path=f'vietnam_{threshold}_higherimps.png',
                      legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)



"""

# Settings
do_multi = True
do_plot = True
do_save = True
save_sim = True
n_runs = 6

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
#    'Test yield': ['test_yield'],
#    'Number quarantined': ['n_quarantined'],
    })

# Run and plot
s0 = make_sim()

#if do_multi:
#    msim = cv.MultiSim(base_sim=s0)
#    msim.run(n_runs=n_runs)
#    msim.reduce()
#    if do_plot:
#        msim.plot(to_plot=to_plot, do_save=do_save, do_show=False, fig_path=f'vietnam.png',
#                  legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)
#    if save_sim:
#        msim.save('vietnam_sim.obj')

if do_multi:
    s0.run(until=today)
    # Copy sims
    sims = []
    for seed in range(n_runs):
        sim = s0.copy()
        sim['rand_seed'] = seed
        sim.set_seed()
        sims.append(sim)
    msim = cv.MultiSim(sims)
    msim.run(n_runs=n_runs, reseed=True, noise=0, keep_people=True)

    #msim = cv.MultiSim(base_sim=sim)
    #msim.run(n_runs=10, reseed=True, noise=0)
    msim.reduce()
    if do_plot:
        msim.plot(to_plot=to_plot, do_save=do_save, do_show=False, fig_path=f'vietnam_scens.png',
                  legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)
    if save_sim:
        msim.save('vietnam_scens.obj')

else:
    s0.run()
    if save_sim:
        s0.save('vietnam_sim.obj')
    if do_plot:
        s0.plot(to_plot=to_plot, do_save=do_save, do_show=False, fig_path=f'vietnam.png',
                  legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)


sc.toc(T)

pl.show()

"""