'''
This script contains analyses for the paper:
"Lessons learned from Vietnam's COVID-19 response:
the role of adaptive behaviour change in epidemic control"
'''

import covasim as cv
import covasim.utils as cvu
import sciris as sc
import pylab as pl
import numpy as np


########################################################################
# Settings
########################################################################
T = sc.tic()
cv.check_save_version()

# Define what to run. All analyses are contained in this single script; the idea if that these should be run sequentially
runoptions = ['quickfit', # Does a quick preliminary calibration. Quick to run, ~30s
              'fitting',  # Searches over parameters and seeds (10,000 runs) and calculates the mismatch for each. Slow to run: ~1hr on Athena
              'finialisecalibration', # Filters the 10,000 runs from the previous step, selects the best-fitting ones, and runs these. Creates a file "vietnam_sim.obj" used by plot_vietnam_calibration for Figure 2
              'mainscens', # Takes the best-fitting runs and projects these forward under different border-reopening scenarios. Creates files "vietnam_sim_drop.obj", "vietnam_sim_remain.obj" and "vietnam_sim_dynamic.obj" used by plot_vietnam_scenarios for Figure 3
              'testingscens'] # Takes the best-fitting runs and projects these forward under different testing scenarios. Creates files "vietnam_sim_{XXX}.obj" used by plot_vietnam_multiscens for Figure 4
whattorun = runoptions[2] #Select which of the above to run

# Settings for plotting and saving
do_plot = True
do_save = True
save_sim = True
keep_people = True
n_runs = 500
today = '2020-10-15'
resfolder = 'results'

to_plot = sc.objdict({
    'Cumulative diagnoses': ['cum_diagnoses'],
    'Cumulative infections': ['cum_infections'],
    'New infections': ['new_infections'],
    'Daily diagnoses': ['new_diagnoses'],
    'Cumulative deaths': ['cum_deaths'],
    'Daily deaths': ['new_deaths'],
})

# Calibration parameters
betas = [i / 10000 for i in range(130, 140, 1)]
change = 0.42


########################################################################
# Make the sim
########################################################################
def make_sim(seed, beta, change=0.42, policy='remain', threshold=5, symp_prob=0.01, end_day=None):

    start_day = '2020-06-15'
    if end_day is None: end_day = '2021-04-30'
    total_pop = 11.9e6 # Population of central Vietnam
    n_agents = 100e3
    pop_scale = total_pop/n_agents

    # Calibration parameters
    pars = {'pop_size': n_agents,
            'pop_infected': 0,
            'pop_scale': pop_scale,
            'rand_seed': seed,
            'beta': beta,
            'start_day': start_day,
            'end_day': end_day,
            'verbose': 0,
            'rescale': True,
            'iso_factor': dict(h=0.5, s=0.01, w=0.01, c=0.1),  # Multiply beta by this factor for people in isolation
            'quar_factor': dict(h=1.0, s=0.2, w=0.2, c=0.2),   # Multiply beta by this factor for people in quarantine
            'location': 'vietnam',
            'pop_type': 'hybrid',
            'age_imports': [50,80],
            'rel_crit_prob': 1.75, # Calibration parameter due to hospital outbreak
            'rel_death_prob': 2., # Calibration parameter due to hospital outbreak
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
    import_end   = sim.day('2020-07-15')
    border_start = sim.day('2020-11-30') # Open borders for one month
    border_end   = sim.day('2020-12-31') # Then close them again
    final_day_ind  = sim.day('2021-04-30')
    imports = np.concatenate((np.array([1, 0, 0, 0, 2, 2, 8, 4, 1, 1, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 2, 3, 1, 1, 3, 0, 3, 0, 1, 6, 1, 5, 0, 0]), # Generated from cv.n_neg_binomial(1, 0.25) but then hard-copied to remove variation when calibrating
                              pl.zeros(border_start-import_end), # No imports from the end of the 1st importation window to the border reopening
                              cv.n_neg_binomial(1, 0.25, border_end-border_start), # Negative-binomial distributed importations each day
                              pl.zeros(final_day_ind-border_end)
                              ))
    pars['n_imports'] = imports

    # Add testing and tracing interventions
    trace_probs = {'h': 1, 's': 0.95, 'w': 0.8, 'c': 0.05}
    trace_time  = {'h': 0, 's': 2, 'w': 2, 'c': 5}
    pars['interventions'] = [
        # Testing and tracing
        cv.test_num(daily_tests=sim.data['new_tests'].rolling(3).mean(), start_day=2, end_day=sim.day('2020-08-22'), symp_test=80, quar_test=80, do_plot=False),
        cv.test_prob(start_day=sim.day('2020-08-23'), end_day=sim.day('2020-11-30'), symp_prob=0.05, asymp_quar_prob=0.5, do_plot=False),
        cv.test_prob(start_day=sim.day('2020-12-01'), symp_prob=symp_prob, asymp_quar_prob=0.5,
                     trigger=cv.trigger('date_diagnosed', 5), triggered_vals={'symp_prob':0.2}, do_plot=False),
        cv.contact_tracing(start_day=0, trace_probs=trace_probs, trace_time=trace_time, do_plot=False),

        # Change death and critical probabilities
        cv.dynamic_pars({'rel_death_prob':{'days':sim.day('2020-08-31'), 'vals':1.0},'rel_crit_prob':{'days':sim.day('2020-08-31'), 'vals':1.0}},do_plot=False), # Assume these were elevated due to the hospital outbreak but then would return to normal

        # Increase precautions (especially mask usage) following the outbreak, which are then abandoned after 40 weeks of low case counts
        cv.change_beta(days=0, changes=change, trigger=cv.trigger('date_diagnosed', 5)),

        # Close schools and workplaces
        cv.clip_edges(days=['2020-07-28', '2020-09-14'], changes=[0.1, 1.], layers=['s'], do_plot=True),
        cv.clip_edges(days=['2020-07-28', '2020-09-05'], changes=[0.1, 1.], layers=['w'], do_plot=False),

        # Dynamically close them again if cases go over the threshold
        cv.clip_edges(days=[170], changes=[0.1], layers=['s'], trigger=cv.trigger('date_diagnosed', threshold)),
        cv.clip_edges(days=[170], changes=[0.1], layers=['w'], trigger=cv.trigger('date_diagnosed', threshold)),
    ]

    if policy != 'remain':
        pars['interventions'] += [cv.change_beta(days=160, changes=1.0, trigger=cv.trigger('date_diagnosed', 2, direction='below', smoothing=28))]
    if policy == 'dynamic':
        pars['interventions'] += [cv.change_beta(days=170, changes=change, trigger=cv.trigger('date_diagnosed', threshold)),
                                  ]

    sim = cv.Sim(pars=pars, datafile="vietnam_data.csv")
    sim.initialize()

    return sim

########################################################################
# Define the analyses
########################################################################

# Quick calibration
if whattorun=='quickfit':
    s0 = make_sim(seed=1, beta=0.0135, change=0.42, end_day=today)
    sims = []
    for seed in range(10):
        sim = s0.copy()
        sim['rand_seed'] = seed
        sim.set_seed()
        sims.append(sim)
    msim = cv.MultiSim(sims)
    msim.run()
    msim.reduce()
    if do_plot:
        msim.plot(to_plot=to_plot, do_save=True, do_show=False, fig_path=f'vietnam.png',
                  legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)


# Full parameter/seed search
elif whattorun=='fitting':
    fitsummary = []
    for beta in betas:
        sc.blank()
        print('---------------\n')
        print(f'Beta: {beta}, change: {change}... ')
        print('---------------\n')
        s0 = make_sim(seed=1, beta=beta, change=change, end_day=today)
        sims = []
        for seed in range(n_runs):
            sim = s0.copy()
            sim['rand_seed'] = seed
            sim.set_seed()
            sims.append(sim)
        msim = cv.MultiSim(sims)
        msim.run()
        fitsummary.append([sim.compute_fit().mismatch for sim in msim.sims])

    sc.saveobj(f'{resfolder}/fitsummary{change}.obj',fitsummary)


# Run calibration with best-fitting seeds and parameters
elif whattorun=='finialisecalibration':
    sims = []
    fitsummary = sc.loadobj(f'{resfolder}/fitsummary{change}.obj')
    for bn, beta in enumerate(betas):
        goodseeds = [i for i in range(n_runs) if fitsummary[bn][i] < 82]
        sc.blank()
        print('---------------\n')
        print(f'Beta: {beta}, change: {change}, goodseeds: {len(goodseeds)}')
        print('---------------\n')
        if len(goodseeds) > 0:
            s0 = make_sim(seed=1, beta=beta, change=change, end_day=today)
            for seed in goodseeds:
                sim = s0.copy()
                sim['rand_seed'] = seed
                sim.set_seed()
                sims.append(sim)

    msim = cv.MultiSim(sims)
    msim.run(keep_people=keep_people)

    if keep_people:
        prop_asymp = []
        prop_asymp_asymp = []
        for sim in msim.sims:
            tt = sim.make_transtree()
            asymp_count = 0
            symp_counts = {}
            asymp_asymp_count = 0
            minind = -5
            maxind = 15
            for _, target_ind in tt.transmissions:
                dd = tt.detailed[target_ind]
                date = dd['date']
                delta = sim.rescale_vec[date] # Increment counts by this much
                if dd['s']: # If there's a source of the infection (i.e. don't count seed infections)

                    # Loop over all undiagnosed infections after July 25
                    if tt.detailed[dd['source']]['date'] <= date and tt.detailed[dd['source']]['date'] >= 40 and np.isnan(dd['t']['date_diagnosed']):

                        # Find what date the target was symptomatic
                        tdate = dd['t']['date_symptomatic']

                        # First, count all the asymptomatic undiagnosed infections
                        if np.isnan(tdate):
                            asymp_count += delta
                        else:
                            ind = int(date - tdate)
                            if ind not in symp_counts:
                                symp_counts[ind] = 0
                            symp_counts[ind] += delta

                        # Second, count all the asymptomatic undiagnosed infections where the source was also asymptomatic
                        if np.isnan(dd['s']['date_symptomatic']):
                            asymp_asymp_count += delta

            prop_asymp.append(asymp_count / (asymp_count + sum(symp_counts.values())))
            prop_asymp_asymp.append(asymp_asymp_count / asymp_count)

        print(np.median(prop_asymp))
        print(np.quantile(prop_asymp, q=0.025))
        print(np.quantile(prop_asymp, q=0.975))
        print(np.median(prop_asymp_asymp))
        print(np.quantile(prop_asymp_asymp, q=0.025))
        print(np.quantile(prop_asymp_asymp, q=0.975))

    if save_sim:
        msim.save(f'{resfolder}/vietnam_sim.obj')
    if do_plot:
        msim.reduce()
        msim.plot(to_plot=to_plot, do_save=do_save, do_show=False, fig_path=f'vietnam.png',
                  legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)



elif whattorun=='mainscens':
    # Load good seeds
    fitsummary = sc.loadobj(f'{resfolder}/fitsummary{change}.obj')
    for policy in ['remain','drop','dynamic']:
        sims = []
        sc.blank()
        print('---------------\n')
        print(f'Starting {policy} policy runs... ')
        print('---------------\n')
        for bn,beta in enumerate(betas):
            s0 = make_sim(seed=1, beta=beta, policy=policy)
            goodseeds = [i for i in range(n_runs) if fitsummary[bn][i] < 82]
            if len(goodseeds)>0:
                for seed in goodseeds:
                    sim = s0.copy()
                    sim['rand_seed'] = seed
                    sim.set_seed()
                    sims.append(sim)
        msim = cv.MultiSim(sims)
        msim.run()

        if save_sim:
            msim.save(f'{resfolder}/vietnam_sim_{policy}.obj')
        if do_plot:
            msim.reduce()
            msim.plot(to_plot=to_plot, do_save=do_save, do_show=False, fig_path=f'vietnam_{policy}.png',
                      legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)



elif whattorun=='testingscens':
    # Load good seeds
    fitsummary = sc.loadobj(f'{resfolder}/fitsummary{change}.obj')
    symp_probs = np.array([0.01048074, 0.02206723, 0.0350389 , 0.04979978, 0.06696701]) # constructed to give testing rates of 10-50% after 10 days
    for sn,sp in enumerate(symp_probs):
        sims = []
        sc.blank()
        print('---------------\n')
        print(f'Starting {sp} testing runs... ')
        print('---------------\n')
        for bn,beta in enumerate(betas):
            s0 = make_sim(seed=1, beta=beta, policy='dynamic', symp_prob=sp)
            goodseeds = [i for i in range(n_runs) if fitsummary[bn][i] < 82]
            if len(goodseeds)>0:
                for seed in goodseeds:
                    sim = s0.copy()
                    sim['rand_seed'] = seed
                    sim.set_seed()
                    sims.append(sim)
        msim = cv.MultiSim(sims)
        msim.run()

        if save_sim:
            msim.save(f'{resfolder}/vietnam_sim_{(sn+1)*10}.obj')
        if do_plot:
            msim.reduce()
            msim.plot(to_plot=to_plot, do_save=do_save, do_show=False, fig_path=f'vietnam_{sp}.png',
                      legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)

