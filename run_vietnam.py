'''
Run Vietnam scenarios for the whole country
'''

import covasim as cv
import sciris as sc
import pylab as pl

today = '2020-10-12'

def make_sim():

    start_day = '2020-10-15'
    end_day = '2021-06-30'
    total_pop = 95.5e6 # Population of central Vietnam
    n_agents = 100e3
    pop_scale = total_pop/n_agents

    # Calibration parameters
    pars = {'pop_size': n_agents,
            'pop_infected': 1,
            'pop_scale': pop_scale,
            'rand_seed': 1,
            'beta': 0.0145,
            'start_day': start_day,
            'end_day': end_day,
            'verbose': .1,
            'rescale': True,
            'iso_factor': dict(h=0.5, s=0.01, w=0.01, c=0.1),  # Multiply beta by this factor for people in isolation
            'quar_factor': dict(h=1.0, s=0.2, w=0.2, c=0.2),   # Multiply beta by this factor for people in quarantine
            'location': 'vietnam',
            'pop_type': 'hybrid',
            }

    # Add testing and tracing interventions
    trace_probs = {'h': 1, 's': 0.95, 'w': 0.8, 'c': 0.05}
    trace_time  = {'h': 0, 's': 2, 'w': 2, 'c': 5}
    pars['interventions'] = [
        cv.test_prob(start_day=0, symp_prob=0.2, asymp_quar_prob=0.2, do_plot=False),
        cv.contact_tracing(start_day=0, trace_probs=trace_probs, trace_time=trace_time, do_plot=False),

        # Increase precautions (especially mask usage) following the outbreak, which are then abandoned after 40 weeks of low case counts
#        cv.change_beta(['2020-07-30'], [0.25]),
#        cv.change_beta(days=0, changes=0.25, trigger=cv.trigger('date_diagnosed',5)),
        #cv.change_beta(days=80, changes=1.0, trigger=cv.trigger('date_diagnosed', 2, direction='below', smoothing=28)),
#        cv.change_beta(days=108, changes=0.4, trigger=cv.trigger('date_diagnosed', 5)),

        # Change death and critical probabilities
#        cv.dynamic_pars({'rel_death_prob':{'days':sim.day('2020-08-31'), 'vals':1.0},'rel_crit_prob':{'days':sim.day('2020-08-31'), 'vals':1.0}}) # Assume these were elevated due to the hospital outbreak but then would return to normal
        ]

    sim = cv.Sim(pars=pars)
    sim.initialize()

    return sim

# Run
T = sc.tic()
cv.check_save_version()

# Settings
do_multi = True
do_plot = True
do_save = True
save_sim = False
n_runs = 15

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
    })

# Run and plot
s0 = make_sim()

if do_multi:
    msim = cv.MultiSim(base_sim=s0)
    msim.run(n_runs=n_runs)
    msim.reduce()
    if do_plot:
        msim.plot(to_plot=to_plot, do_save=do_save, do_show=False, fig_path=f'vietnam_scens.png',
                  legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)
    if save_sim:
        msim.save('vietnam_scens.obj')

#if domulti:
#    s0.run(until=today)
#    # Copy sims
#    sims = []
#    for seed in range(n_runs):
#        sim = s0.copy()
#        sim['rand_seed'] = seed
#        sim.set_seed()
#        sims.append(sim)
#    msim = cv.MultiSim(sims)
#    msim.run(n_runs=n_runs, reseed=True, noise=0, keep_people=True)

    #msim = cv.MultiSim(base_sim=sim)
    #msim.run(n_runs=10, reseed=True, noise=0)
#    msim.reduce()
else:
    s0.run()
    if save_sim:
        s0.save('vietnam_sim.obj')
    if do_plot:
        s0.plot(to_plot=to_plot, do_save=do_save, do_show=False, fig_path=f'vietnam.png',
                  legend_args={'loc': 'upper left'}, axis_args={'hspace': 0.4}, interval=21)


sc.toc(T)

pl.show()

