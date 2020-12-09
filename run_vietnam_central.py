'''
Run calibration for central Vietnam
'''

import covasim as cv
import covasim.utils as cvu
import sciris as sc
import pylab as pl
import numpy as np


# Make the sim
def make_sim(seed, beta, change=0.42, policy='remain', threshold=5, end_day=None):

    start_day = '2020-06-15'
    if end_day is None: end_day = '2021-02-28'
    total_pop = 11.9e6 #95.5e6 # Population of central Vietnam
    n_agents = 100e3
    pop_scale = total_pop/n_agents

    # Calibration parameters
    pars = {'pop_size': n_agents,
            'pop_infected': 1,
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
    import_start = sim.day('2020-06-15')
    import_end   = sim.day('2020-07-15')
    border_start = sim.day('2020-11-30')
    final_day_ind  = sim.day('2021-02-28')
    imports = np.concatenate((pl.zeros(import_start), # No imports until the import start day
#                              pl.ones(import_end-import_start)*2, # 20 imports/day over the first importation window
                              cv.n_neg_binomial(1, 0.25, import_end-import_start),
                              pl.zeros(border_start-import_end), # No imports from the end of the 1st importation window to the border reopening
                              cv.n_neg_binomial(1, 0.5, final_day_ind-border_start) # Negative-binomial distributed importations each day
                              ))
    pars['n_imports'] = imports

    # Add testing and tracing interventions
    trace_probs = {'h': 1, 's': 0.95, 'w': 0.8, 'c': 0.05}
    trace_time  = {'h': 0, 's': 2, 'w': 2, 'c': 5}
    pars['interventions'] = [
        # Testing and tracing
        cv.test_num(daily_tests=sim.data['new_tests'].rolling(3).mean(), start_day=2, end_day=sim.day('2020-08-22'), symp_test=80, quar_test=80, do_plot=False),
        #cv.test_num(daily_tests=sim.data['new_tests'].rolling(3).mean(), start_day=2, end_day=sim.day('2020-07-25'), symp_test=120, quar_test=120, do_plot=False),
        cv.test_prob(start_day=sim.day('2020-08-23'), end_day=sim.day('2020-11-30'), symp_prob=0.05, asymp_quar_prob=0.5, do_plot=False),
        cv.test_prob(start_day=sim.day('2020-12-01'), symp_prob=0.05, asymp_quar_prob=0.5,
                     trigger=cv.trigger('date_diagnosed', 5), triggered_vals={'symp_prob':0.2}, do_plot=False),
        cv.contact_tracing(start_day=0, trace_probs=trace_probs, trace_time=trace_time, do_plot=False),

        # Change death and critical probabilities
        cv.dynamic_pars({'rel_death_prob':{'days':sim.day('2020-08-31'), 'vals':1.0},'rel_crit_prob':{'days':sim.day('2020-08-31'), 'vals':1.0}},do_plot=False), # Assume these were elevated due to the hospital outbreak but then would return to normal

        # Increase precautions (especially mask usage) following the outbreak, which are then abandoned after 40 weeks of low case counts
        #cv.change_beta(days=0, changes=0.25, layers=['c','w','s'], trigger=cv.trigger('date_diagnosed', 5)),
        #cv.change_beta(days=0, changes=change, layers=['c','w','s'], trigger=cv.trigger('date_diagnosed', 5)),
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


T = sc.tic()
cv.check_save_version()

whattorun = ['quickestfit', 'quickfit', 'fitting', 'finialisecalibration', 'transmissionanalysis', 'quickscens', 'mainscens', 'multiscens'][2]
do_plot = True
do_save = True
save_sim = True
keep_people = False
n_runs = 500
#betas = [i / 10000 for i in range(135, 155, 2)]
#changes = [i / 100 for i in range(26, 80, 7)]
today = '2020-10-15'
highbetas = [i / 10000 for i in range(130, 135, 1)]
midbetas = [i / 10000 for i in range(130, 140, 1)]  # [i / 10000 for i in range(115, 125, 1)]
betas = [highbetas, midbetas][1]
change = [0.26, 0.42][1]
changes = [0.42]

# Quickest possible calibration
if whattorun=='quickestfit':
    sim = make_sim(seed=1, beta=0.0145, end_day=today)
    sim.run(keep_people=True)
    tt = sim.make_transtree()

    # Calculate
    asymp_count = 0
    symp_counts = {}
    minind = -5
    maxind = 15
    for _, target_ind in tt.transmissions:
        dd = tt.detailed[target_ind]
        date = dd['date']
        delta = sim.rescale_vec[date] # Increment counts by this much
        if dd['s']:
            if tt.detailed[dd['source']]['date'] <= date and tt.detailed[dd['source']]['date'] >= 40 and np.isnan(dd['t']['date_diagnosed']) and np.isnan(dd['s']['date_symptomatic']): # Skip dynamical scaling reinfections
                tdate = dd['t']['date_symptomatic']
                if np.isnan(tdate):
                    asymp_count += delta
                else:
                    ind = int(date - tdate)
                    if ind not in symp_counts:
                        symp_counts[ind] = 0
                    symp_counts[ind] += delta

    asymp_prop = asymp_count / (asymp_count + sum(symp_counts.values()))

    # Transmission by layer
    layer_keys = list(sim.people.layer_keys())
    layer_mapping = {k: i for i, k in enumerate(layer_keys)}
    n_layers = len(layer_keys)
    layer_counts = np.zeros((sim.npts, n_layers))
    for source_ind, target_ind in tt.transmissions:
        dd = tt.detailed[target_ind]
        if np.isnan(dd['t']['date_diagnosed']):
            date = dd['date']
            layer_num = layer_mapping[dd['layer']]
            layer_counts[date, layer_num] += sim.rescale_vec[date]

    # # Calculate the proportion of undiagnosed people that didn't transmit
    # n_targets = np.nan + np.zeros(sim['pop_size'])
    # n_targets_all = np.nan + np.zeros(sim['pop_size'])
    # for i in range(sim['pop_size']):
    #     if tt.sources[i] is not None:
    #         n_targets_all[i] = len(tt.targets[i])
    #         if np.isnan(sim.people[i].date_diagnosed): # They weren't diagnosed: let's see how many people they transmitted to
    #             n_targets[i] = len(tt.targets[i])
    # n_target_inds = sc.findinds(~np.isnan(n_targets))
    # n_targets = n_targets[n_target_inds]
    #
    # n_target_all_inds = sc.findinds(~np.isnan(n_targets_all))
    # n_targets_all = n_targets_all[n_target_all_inds]
    #
    # # Analysis for undiagnosed infections
    # max_infections = n_targets.max()
    # bins = np.arange(0, max_infections + 2)
    # counts = np.histogram(n_targets, bins)[0]
    # bins = bins[:-1]  # Remove last bin since it's an edge
    # total_counts = counts * bins
    # total_counts = total_counts / total_counts.sum() * 100
    #
    # # Analysis for all infections
    # max_infections_all = n_targets_all.max()
    # bins_all = np.arange(0, max_infections_all + 2)
    # counts_all = np.histogram(n_targets_all, bins_all)[0]
    # bins_all = bins_all[:-1]  # Remove last bin since it's an edge
    # total_counts_all = counts_all * bins_all
    # total_counts_all = total_counts_all / total_counts_all.sum() * 100

    # Other stats
    ever_exp = cvu.defined(sim.people.date_exposed)
    exp_postjul25 = sim.people.uid[sim.people.date_exposed>40]
    ever_symp = cvu.defined(sim.people.date_symptomatic)
    symp_postjul25 = sim.people.uid[sim.people.date_symptomatic>40]
    asyms = np.setdiff1d(ever_exp, ever_symp)
    asyms_postjul25 = np.setdiff1d(exp_postjul25, symp_postjul25)
    diag_inds = cvu.true(sim.people.diagnosed)
    diag_postjul25 = sim.people.uid[sim.people.date_diagnosed>40]
    undiag_inds = np.setdiff1d(ever_exp, diag_inds)
    undiag_postjul25 = np.setdiff1d(exp_postjul25, diag_postjul25)

    diag_symp = cvu.true(sim.people.diagnosed[cvu.defined(sim.people.date_symptomatic)]) # Diagnosed and symptomatic
    diag_asymp = cvu.true(sim.people.diagnosed[asyms]) # Diagnosed and asymptomatic
    undiag_symp = np.intersect1d(undiag_inds, ever_symp) # Undiagnosed and symptomatic
    undiag_asymp = np.intersect1d(undiag_inds, asyms) # Undiagnosed and asymptomatic


    tt.n_targets

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
    # Plot settings
    to_plot = sc.objdict({
        'Cumulative diagnoses': ['cum_diagnoses'],
        'Cumulative infections': ['cum_infections'],
        'New infections': ['new_infections'],
        'Daily diagnoses': ['new_diagnoses'],
        'Cumulative deaths': ['cum_deaths'],
        'Daily deaths': ['new_deaths'],
        'Daily tests': ['new_tests'],
        'Cumulative tests': ['cum_tests'],
        })

    msim.plot(to_plot=to_plot, do_save=True, do_show=False, fig_path=f'vietnam.png',
              legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)


# Iterate for calibration
elif whattorun=='fitting':
    highbetas = [i / 10000 for i in range(130, 135, 1)]
    midbetas  = [i / 10000 for i in range(130, 140, 1)]#[i / 10000 for i in range(115, 125, 1)]
    betas = [highbetas, midbetas][1]
    change = [0.26, 0.42][1]
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

    sc.saveobj(f'fitsummary{change}.obj',fitsummary)


elif whattorun=='finialisecalibration':
    sims = []
    for cn, change in enumerate(changes):
        fitsummary = sc.loadobj(f'searches/fitsummary{change}_1.obj')
        for bn, beta in enumerate(betas):
            goodseeds = [i for i in range(n_runs) if fitsummary[bn][i] < 80]
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

    # Calculate and store some transmission dynamics
#    for sim in msim.sims:
#        tt = sim.make_transtree()
#        n_targets = tt.count_targets()


    to_plot = sc.objdict({
        'Cumulative diagnoses': ['cum_diagnoses'],
        'Cumulative infections': ['cum_infections'],
        'New infections': ['new_infections'],
        'Daily diagnoses': ['new_diagnoses'],
        'Cumulative deaths': ['cum_deaths'],
        'Daily deaths': ['new_deaths'],
    })

    if save_sim:
        msim.save(f'vietnam_sim.obj', keep_people=keep_people)
    if do_plot:
        msim.reduce()
        msim.plot(to_plot=to_plot, do_save=do_save, do_show=False, fig_path=f'vietnam.png',
                  legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)

elif whattorun=='transmissionanalysis':
    msim = sc.loadobj('vietnam_sim.obj')

    # Analyse the undiagnosed people: who are they, why didn't they get diagnosed?
    ever_exp = cvu.defined(sim.people.date_exposed)
    ever_symp = cvu.defined(sim.people.date_symptomatic)
    asyms = np.setdiff1d(ever_exp, ever_symp)
    tested_inds = cvu.true(sim.people.tested)
    diag_inds = cvu.true(sim.people.diagnosed)
    undiag_inds = np.setdiff1d(ever_exp, diag_inds)

    diag_symp = cvu.true(sim.people.diagnosed[cvu.defined(sim.people.date_symptomatic)]) # Diagnosed and symptomatic
    diag_asymp = cvu.true(sim.people.diagnosed[asyms]) # Diagnosed and asymptomatic
    undiag_symp = np.intersect1d(undiag_inds, ever_symp) # Undiagnosed and symptomatic
    undiag_asymp = np.intersect1d(undiag_inds, asyms) # Undiagnosed and asymptomatic

    cvu.defined(sim.people.date_known_contact)

elif whattorun=='quickscens':
    print('---------------\n')
    print(f'Starting {whattorun}... ')
    print('---------------\n')
    # Load good seeds
    fitsummary = sc.loadobj(f'searches/fitsummary{0.42}_1.obj')
    for policy in ['remain','drop','dynamic']:
        sims = []
        sc.blank()
        print('---------------\n')
        print(f'Starting {policy} policy runs... ')
        print('---------------\n')
        for bn,beta in enumerate(betas):
            s0 = make_sim(seed=1, beta=beta, policy=policy)
            goodseeds = [i for i in range(n_runs) if fitsummary[bn][i] < 60]
            if len(goodseeds)>0:
                for seed in goodseeds:
                    sim = s0.copy()
                    sim['rand_seed'] = seed
                    sim.set_seed()
                    sims.append(sim)
        print('---------------\n')
        print(f'Number of sims: {len(sims)}... ')
        print('---------------\n')
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

#        if save_sim:
#            msim.save(f'results4dec/vietnam_sim_{policy}.obj')
        if do_plot:
            msim.reduce()
            msim.plot(to_plot=to_plot, do_save=do_save, do_show=False, fig_path=f'vietnam_q_{policy}.png',
                      legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)



elif whattorun=='mainscens':
    # Load good seeds
    fitsummary = sc.loadobj(f'searches/fitsummary{0.42}.obj')
    for policy in ['remain','drop','dynamic']:
        sims = []
        sc.blank()
        print('---------------\n')
        print(f'Starting {policy} policy runs... ')
        print('---------------\n')
        for bn,beta in enumerate(betas):
            s0 = make_sim(seed=1, beta=beta, policy=policy)
            goodseeds = [i for i in range(n_runs) if fitsummary[bn][i] < 73]
            if len(goodseeds)>0:
                for seed in goodseeds:
                    sim = s0.copy()
                    sim['rand_seed'] = seed
                    sim.set_seed()
                    sims.append(sim)
        msim = cv.MultiSim(sims)
        msim.run(parallel=False)
        to_plot = sc.objdict({
            'Cumulative diagnoses': ['cum_diagnoses'],
            'Cumulative infections': ['cum_infections'],
            'New infections': ['new_infections'],
            'Daily diagnoses': ['new_diagnoses'],
            'Cumulative deaths': ['cum_deaths'],
            'Daily deaths': ['new_deaths'],
            })

        if save_sim:
            msim.save(f'results4dec/vietnam_sim_{policy}.obj')
        if do_plot:
            msim.reduce()
            msim.plot(to_plot=to_plot, do_save=do_save, do_show=False, fig_path=f'vietnam_{policy}.png',
                      legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)


elif whattorun=='multiscens':
    # Load good seeds
    fitsummary = sc.loadobj(f'searches/fitsummary{0.42}.obj')
    thresholds = np.arange(10,60,10)
    for threshold in thresholds:
        sims = []
        sc.blank()
        print('---------------\n')
        print(f'Starting {threshold} policy runs... ')
        print('---------------\n')
        for bn,beta in enumerate(betas):
            s0 = make_sim(seed=1, beta=beta, policy='dynamic', threshold=threshold)
            goodseeds = [i for i in range(n_runs) if fitsummary[bn][i] < 70]
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
            msim.plot(to_plot=to_plot, do_save=do_save, do_show=False, fig_path=f'vietnam_{threshold}.png',
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