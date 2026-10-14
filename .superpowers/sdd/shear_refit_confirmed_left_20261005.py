import runpy
from pathlib import Path
n=runpy.run_path(".superpowers/sdd/shear_refit_reuse_alignment_20261005.py")
g=n["main"].__globals__
g["SOURCES"]=dict(g["SOURCES"])
g["SOURCES"]["left_before"]=g["ROOT"] / "calibration/shear_refit_20261005_after_button/fit/left_repeat_after.json"
g["SOURCES"]["left"]=g["ROOT"] / "calibration/shear_refit_20261005_after_button/fit/left_confirmed_repeat.json"
g["REPORT"]=Path(".superpowers/sdd/shear-refit-confirmed-left-report-20261005.json")
g["main"]()
