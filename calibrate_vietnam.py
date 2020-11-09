'''
Calibrate Vietnam
'''

import numpy as np
import pylab as pl
import sciris as sc
import covasim as cv
import scipy as sp
import optuna as op

cv.check_save_version()


class Calibration:

    def __init__(self, storage):

        # Settings
        self.pop_size = 100e3 # Number of agents
        self.start_day = '2020-06-15'
        self.end_day = '2020-10-12' # Change final day here
        self.datafile = 'vietnam_data.csv'
        self.total_pop = 95.5e6

        # Saving and running
        self.n_trials  = 50 # Number of sequential Optuna trials
        self.n_workers = 1 # Number of parallel Optuna threads -- incompatible with n_runs > 1
        self.n_runs    = 50 # Number of sims being averaged together in a single trial -- incompatible with n_workers > 1
        self.storage   = storage # Database location
        self.name      = 'vietnam_calibration' # Optuna study name -- not important but required

        # Plotting options
        self.to_plot = ['cum_infections', 'new_infections', 'cum_tests', 'new_tests', 'cum_diagnoses', 'new_diagnoses', 'cum_deaths', 'new_deaths']


    def create_sim(self, x, verbose=0.1):
        ''' Create the simulation from the parameters '''

        if isinstance(x, dict):
            pars, pkeys = self.get_bounds() # Get parameter guesses
            x = [x[k] for k in pkeys]

        # Define and load the data
        self.calibration_parameters = x

        # Convert parameters
        beta         = x[0]
        imports      = x[1]
        symp_test    = x[2]

        # Create parameters
        pars = dict(
            pop_size        = self.pop_size,
            pop_scale       = self.total_pop/self.pop_size,
            pop_infected    = 10,
            beta            = beta,
            start_day       = self.start_day,
            end_day         = self.end_day,
            rescale         = True,
            verbose         = verbose,
            iso_factor      = dict(h=0.5, s=0.01, w=0.01, c=0.1), # Multiply beta by this factor for people in isolation
            quar_factor     = dict(h=1.0, s=0.2, w=0.2, c=0.2), # Multiply beta by this factor for people in quarantine
            location        = 'vietnam',
            pop_type        = 'hybrid',
            age_imports     = [50, 80],
            rel_crit_prob   = 1.25,  # Calibration parameter due to hospital outbreak
            rel_death_prob  = 1.25,  # Calibration parameter due to hospital outbreak
        )

        # Make a sim without parameters, just to load in the data to use in the testing intervention and to get the sim days
        sim = cv.Sim(start_day=self.start_day, datafile=self.datafile)

        pars['dur_imports'] = sc.dcp(sim.pars['dur'])
        pars['dur_imports']['exp2inf'] = {'dist': 'lognormal_int', 'par1': 0.0, 'par2': 0.0}
        pars['dur_imports']['inf2sym'] = {'dist': 'lognormal_int', 'par1': 0.0, 'par2': 0.0}
        pars['dur_imports']['sym2sev'] = {'dist': 'lognormal_int', 'par1': 0.0, 'par2': 2.0}
        pars['dur_imports']['sev2crit'] = {'dist': 'lognormal_int', 'par1': 1.0, 'par2': 3.0}
        pars['dur_imports']['crit2die'] = {'dist': 'lognormal_int', 'par1': 3.0, 'par2': 3.0}

        # Add interventions
        trace_probs = {'h': 1, 's': 0.95, 'w': 0.8, 'c': 0.05}
        trace_time = {'h': 0, 's': 2, 'w': 2, 'c': 5}
        pars['interventions'] = [
            # Testing and tracing
            cv.test_num(daily_tests=sim.data['new_tests'], start_day=sim.day('2020-07-01'), end_day=sim.day('2020-08-22'), symp_test=symp_test, quar_test=symp_test / 2, do_plot=False),
            cv.test_prob(start_day=sim.day('2020-08-23'), symp_prob=0.05, asymp_quar_prob=0.05, do_plot=False),
            cv.contact_tracing(start_day=0, trace_probs=trace_probs, trace_time=trace_time, do_plot=False),

            cv.dynamic_pars({'n_imports': {'days': [sim.day('2020-07-20'), sim.day('2020-07-25')], 'vals': [imports, 0]}}, do_plot=False),
            cv.dynamic_pars({'n_imports': {'days': [sim.day('2020-11-01'), sim.day('2020-11-02')], 'vals': [20, 0]}}, do_plot=False),

            cv.change_beta(days=0, changes=0.25, trigger=cv.trigger('date_diagnosed', 5)),
            cv.change_beta(days=80, changes=1.0, trigger=cv.trigger('date_diagnosed', 2, direction='below', smoothing=28)),
            cv.change_beta(days=140, changes=0.4, trigger=cv.trigger('date_diagnosed', 5)),

            # Change death and critical probabilities
            cv.dynamic_pars({'rel_death_prob': {'days': sim.day('2020-08-31'), 'vals': 1.0}, 'rel_crit_prob': {'days': sim.day('2020-08-31'), 'vals': 1.0}}) # Assume these were elevated due to the hospital outbreak but then would return to normal
        ]

        # Create the sim
        sim = cv.Sim(pars, datafile=self.datafile)

        self.sim = sim

        return sim


    def get_bounds(self):
        ''' Set parameter starting points and bounds -- NB, only lower and upper bounds used for fitting '''
        pdict = sc.objdict(
            beta         = dict(best=0.015, lb=0.012, ub=0.020),
            imports      = dict(best=20,    lb=10,    ub=50),
            symp_test    = dict(best=50,    lb=5,     ub=200),
        )

        # Convert from dicts to arrays
        pars = sc.objdict()
        for key in ['best', 'lb', 'ub']:
            pars[key] = np.array([v[key] for v in pdict.values()])

        return pars, pdict.keys()


    def run_msim(self):
        ''' Run the simulation'''
        if self.n_runs == 1:
            sim = self.sim
            sim.run()
        else:
            msim = cv.MultiSim(base_sim=self.sim)
            msim.run(n_runs=self.n_runs)

            allmismatches = [sim.compute_fit().mismatch for sim in msim.sims]
            percentlt100 = len([i for i in range(self.n_runs) if allmismatches[i] < 100])

        self.msim = msim
        self.mismatch = -percentlt100

        return msim


    def objective(self, x):
        ''' Define the objective function we are trying to minimize '''
        self.create_sim(x=x)
        self.run_msim()
        return self.mismatch


    def op_objective(self, trial):
        ''' Define the objective for Optuna '''
        pars, pkeys = self.get_bounds() # Get parameter guesses
        x = np.zeros(len(pkeys))
        for k,key in enumerate(pkeys):
            x[k] = trial.suggest_uniform(key, pars.lb[k], pars.ub[k])

        return self.objective(x)

    def worker(self):
        ''' Run a single Optuna worker '''
        study = op.load_study(storage=self.storage, study_name=self.name)
        return study.optimize(self.op_objective, n_trials=self.n_trials)


    def run_workers(self):
        ''' Run allworkers -- parallelized if each sim is not parallelized '''
        if self.n_workers == 1:
            self.worker()
        else:
            sc.parallelize(self.worker, self.n_workers)
        return


    def make_study(self):
        try: op.delete_study(storage=self.storage, study_name=self.name)
        except: pass
        return op.create_study(storage=self.storage, study_name=self.name)


    def load_study(self):
        return op.load_study(storage=self.storage, study_name=self.name)


    def get_best_pars(self, print_mismatch=True):
        ''' Get the outcomes of a calibration '''
        study = self.load_study()
        output = study.best_params
        if print_mismatch:
            print(f'Mismatch: {study.best_value}')
        return output


    def calibrate(self):
        ''' Perform the calibration '''
        self.make_study()
        self.run_workers()
        output = self.get_best_pars()
        return output


    def save(self):
        pars_calib = self.get_best_pars()
        sc.savejson(f'calibrated_parameters_{self.until}_{self.state}.json', pars_calib)


if __name__ == '__main__':

    recalibrate = True # Whether to run the calibration
    do_plot     = False # Whether to plot results
    storage     = f'sqlite:///example_calibration.db' # Optuna database location
    verbose     = 0.1 # How much detail to print

    cal = Calibration(storage)

    # Plot initial
    if do_plot:
        print('Running initial uncalibrated simulation...')
        pars, pkeys = cal.get_bounds() # Get parameter guesses
        sim = cal.create_sim(pars.best, verbose=verbose)
        sim.run()
        sim.plot(to_plot=cal.to_plot)
        pl.gcf().suptitle('Initial parameter values')
        cal.objective(pars.best)
        pl.pause(1.0) # Ensure it has time to render

    # Calibrate
    if recalibrate:
        print(f'Starting calibration...')
        T = sc.tic()
        pars_calib = cal.calibrate()
        sc.toc(T)
    else:
        pars_calib = cal.get_best_pars()

    # Plot result
    if do_plot:
        print('Plotting result...')
        x = [pars_calib[k] for k in pkeys]
        sim = cal.create_sim(x, verbose=verbose)
        sim.run()
        sim.plot(to_plot=cal.to_plot)
        pl.gcf().suptitle('Calibrated parameter values')




print('Done.')