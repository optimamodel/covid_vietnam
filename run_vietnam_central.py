'''
Run calibration for central Vietnam
'''

import covasim as cv
import sciris as sc
import pylab as pl

today = '2020-10-15'

def make_sim(seed, beta):

    start_day = '2020-06-15'
    end_day = today #'2020-12-31'
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
            'verbose': .1,
            'rescale': True,
            'iso_factor': dict(h=0.5, s=0.01, w=0.01, c=0.1),  # Multiply beta by this factor for people in isolation
            'quar_factor': dict(h=1.0, s=0.2, w=0.2, c=0.2),   # Multiply beta by this factor for people in quarantine
            'location': 'vietnam',
            'pop_type': 'hybrid',
#            'n_imports': {'dist': 'poisson', 'par1': 5.0},
            'age_imports': [50,80],
            'rel_crit_prob': 1.5, # Calibration parameter due to hospital outbreak
            'rel_death_prob': 1.5, # Calibration parameter due to hospital outbreak
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
        # Testing and tracing
        cv.test_num(daily_tests=sim.data['new_tests'], start_day=sim.day('2020-07-01'), end_day=sim.day('2020-08-22'), symp_test=100, quar_test=100, do_plot=False),
#        cv.test_num(daily_tests=7000, start_day=sim.day('2020-08-23'), symp_test=60.0, quar_test=50.,do_plot=False),
        cv.test_prob(start_day=sim.day('2020-08-23'), symp_prob=0.05, asymp_quar_prob=0.05, do_plot=False),
        cv.contact_tracing(start_day=0, trace_probs=trace_probs, trace_time=trace_time, do_plot=False),

        # Introduce imported cases in mid-July and then again in September (representing reopening borders)
        cv.dynamic_pars({'n_imports': {'days': [sim.day('2020-07-20'), sim.day('2020-07-25')], 'vals': [20, 0]}}, do_plot=False),
        cv.dynamic_pars({'n_imports': {'days': [sim.day('2020-11-15'), sim.day('2020-11-16')], 'vals': [20, 0]}}, do_plot=False),

        # Increase precautions (especially mask usage) following the outbreak, which are then abandoned after 40 weeks of low case counts
#        cv.change_beta(['2020-07-30'], [0.25]),
        cv.change_beta(days=0, changes=0.25, trigger=cv.trigger('date_diagnosed',5)),
        cv.change_beta(days=80, changes=1.0, trigger=cv.trigger('date_diagnosed', 2, direction='below', smoothing=28)),
        cv.change_beta(days=140, changes=0.4, trigger=cv.trigger('date_diagnosed', 5)),

        # Change death and critical probabilities
        cv.dynamic_pars({'rel_death_prob':{'days':sim.day('2020-08-31'), 'vals':1.0},'rel_crit_prob':{'days':sim.day('2020-08-31'), 'vals':1.0}},do_plot=False) # Assume these were elevated due to the hospital outbreak but then would return to normal
        ]

    sim = cv.Sim(pars=pars, datafile="vietnam_data.csv")
    sim.initialize()

    return sim


T = sc.tic()
cv.check_save_version()

do_fitting = True
do_plot = True
do_save = True
save_sim = True
n_runs = 100

# Iterate for calibration
if do_fitting:
    fitsummary = {}
    fitsummary['allmismatches'] = []
    fitsummary['percentlt75'] = []
    fitsummary['percentlt100'] = []

    betas = [i / 10000 for i in range(140, 151, 1)]
    for beta in betas:
        s0 = make_sim(seed=1, beta=beta)
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


else:
    # Load good seeds
    fitsummary = sc.loadobj('fitsummary.obj')
    betas = [i / 10000 for i in range(140, 151, 1)]
    sims = []
    for bn,beta in enumerate(betas):
        s0 = make_sim(seed=1, beta=beta)
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

    if do_plot:
        msim.plot(to_plot=to_plot, do_save=do_save, do_show=False, fig_path=f'vietnam.png',
                  legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)
    if save_sim:
        msim.save('vietnam_sim.obj')


'''
s0 = make_sim(seed=1, beta=0.0145)
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


'''

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