"""CPL attainment from Template_Input_Data_CPL.xlsx (one file per class per semester).

read_template -> compute -> run_checks / class_attainment.
The workbook's own formula sheets are only a reference; see compute.py.
"""
from .checks import all_ok, run_checks
from .compute import Result, class_attainment, compute
from .template import Template, read_template

__all__ = ["Template", "Result", "read_template", "compute",
           "class_attainment", "run_checks", "all_ok"]
