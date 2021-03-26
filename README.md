# Analysis of COVID-19 transmission in Vietnam

This repository contains the code and data for the manuscript "Lessons learned from Vietnam's COVID-19 response: the role of adaptive behaviour change in epidemic control". Manuscript: https://doi.org/10.1101/2020.12.18.20248454

## Usage

1. The files for generating Figure 1 are in the fig1 folder. Figure 1 can be created by running `fig1-epi-stats.R`. This will save a file called `output/fig1.png`.
2. The file `run_vietnam_central.py` can be configured to (1) calibrate the model, and (2) run scenarios. Choose which of these you want to do by setting `whattorun`. If you set `save_sim = True`, the simulations will be saved as `*.obj` to the `results` folder. 
3. Run `plot_vietnam_calibration.py`, `plot_vietnam_scenarios.py`, and `plot_vietnam_multiscens.py` to load the `*.obj` files generated by the previous step and generate Figures 2-4 respectively.
