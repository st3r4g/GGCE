#!/usr/bin/env python3

import argparse
from argparse import HelpFormatter, ArgumentDefaultsHelpFormatter
from operator import attrgetter


# https://stackoverflow.com/questions/
# 12268602/sort-argparse-help-alphabetically
class SortingHelpFormatter(ArgumentDefaultsHelpFormatter, HelpFormatter):
    def add_arguments(self, actions):
        actions = sorted(actions, key=attrgetter('option_strings'))
        super(SortingHelpFormatter, self).add_arguments(actions)


def global_parser(sys_argv):

    ap = argparse.ArgumentParser(formatter_class=SortingHelpFormatter)

    ap.add_argument(
        '--force', dest='force', default=False, action='store_true',
        help='Overrides failsafes, automatically applies "yes" to otherwise '
        'required user inputs.'
    )

    ap.add_argument(
        '--debug', default=False, dest='debug', action='store_true',
        help='Enables the debug logging stream to stdout.'
    )

    ap.add_argument(
        '--package_dir', dest='package_dir', default='packages',
        help="The location of the packages."
    )

    subparsers = ap.add_subparsers(
        help='Choices for various priming, execution and post-processing '
        'protocols.', dest='protocol'
    )

    # (1) ---------------------------------------------------------------------
    prime_sp = subparsers.add_parser(
        "prime", formatter_class=SortingHelpFormatter,
        description='Prime the computation for submission by creating the '
        'appropriate directories and writing the SLURM submit file.'
    )
    prime_sp.add_argument(
        '-c', '--configs', type=int, nargs='+', default=None, dest='c_to_run',
        help='Indexes the configs within a package to run. Defaults to '
        'running all configs in the package.'
    )
    prime_sp.add_argument(
        '--linspacek', default=False, dest='linspacek',
        action='store_true',
        help='If True, then the user is required to provide three values for '
        'the -k flag: the k0, kf and total number of k points.'
    )
    prime_sp.add_argument(
        '--info', dest='info', default=None,
        help='Extra information about the package which is appended to the '
        'package name.'
    )

    # Local stuff can be done easily via Jupyter notebooks
    # prime_sp.add_argument(
    #     '--local', dest='local', default=False, action='store_true',
    #     help='Saves a bash script instead of SLURM.'
    # )
    # prime_sp.add_argument(
    #     '-r', '--rule', dest='rule', default=0, type=int,
    #     help="Special rules for further restricting the configuration space."
    #     "Default is 0 (no rule)."
    # )

    req = prime_sp.add_argument_group("required")
    req.add_argument(
        '-N', type=int, nargs='+', default=None, dest='N',
        help='Number of bosons.', required=True
    )
    req.add_argument(
        '-M', type=int, nargs='+', default=None, dest='M',
        help='Maximal cloud extent.', required=True
    )
    req.add_argument(
        '--eta', type=float, nargs='+', default=None, dest='eta',
        help='Broadening parameter.', required=True
    )
    req.add_argument(
        '-k', type=float, nargs='+', default=None, dest='k_units_pi',
        help='Values for k in units of pi.', required=True
    )
    req.add_argument(
        '-P', '--package', type=str, default=None, dest='package',
        help='Name of the package to prime. Packages must be contained in the '
        '`package_dir` directory.', required=True
    )

    # (2) ---------------------------------------------------------------------
    execute_sp = subparsers.add_parser(
        "execute", formatter_class=SortingHelpFormatter,
        description='Submits jobs to the job controller or runs them locally '
        'depending on the prime step.'
    )
    execute_sp.add_argument(
        '--bash', default=False, dest='bash',
        action='store_true', help='Run using bash (locally) instead of sbatch'
    )
    execute_sp.add_argument(
        '--dryrun', default=False, dest='dryrun',
        action='store_true', help='Run in dryrun mode. This is different '
        'from debug in the sense that an actual job will be run/submitted, '
        'but all values for G will be randomly sampled, and there will be '
        'no actual GGCE calculations run.'
    )

    slurm = execute_sp.add_argument_group(
        "SLURM", "SLURM script parameters used to override defaults "
        "in the slurm_config.yaml file. Note that some parameters must "
        "be set in the config. The parameter priority goes as follows: "
        "CL args (here) override the config, and the config overrides "
        "default CL args (i.e., when a CL arg is not specified)."
    )

    slurm.add_argument(
        '-p', '--partition', dest='partition', default=None, type=str
    )
    slurm.add_argument(
        '-c', '--constraint', dest='constraint', default=None, type=str
    )
    slurm.add_argument('-q', '--queue', dest='qos', default=None, type=str)
    slurm.add_argument('-N', '--nodes', dest='N_nodes', default=None, type=int)
    slurm.add_argument(
        '-d', '--threads', default=None, dest='threads_per_task', type=int,
        help='Number of threads/MPI process.'
    )
    slurm.add_argument(
        '-s', '--tasks_per_node', dest='tasks_per_node', default=None,
        type=int
    )
    slurm.add_argument(
        '--mem_per_node', dest='mem_per_node', default=None, type=str,
        help="Memory per node, in format e.g. 62000M"
    )

    slurm.add_argument('--email', dest='email', default=None, type=str)

    slurm.add_argument(
        '--t_max', dest='t_max', default=None, type=str,
        help="The maximum run-time for a single SLURM submission. Jobs will "
        "temrinate after this elapsed time with a KILL signal sent to the "
        "process. This also represents the maximum time for a single script "
        "before being killed in the requeue process."
    )
    slurm.add_argument(
        '--t_min', dest='t_min', default=None, type=str,
        help="The minimum run-time for a single SLURM submission. Used to "
        "help the job controller find open spaces in the schedule. Jobs will "
        "have runtime limits somewhere between t_min and t_max."
    )
    slurm.add_argument(
        '--t_total', dest='t_total', default=None, type=str,
        help="The total time limit for requeue jobs."
    )

    slurm.add_argument(
        '--job_name', dest='job_name', default=None, type=str
    )
    slurm.add_argument(
        '--job_data_directory', dest='job_data_directory',
        default=None, type=str
    )

    slurm.add_argument(
        '--requeue', dest='requeue', default=False,
        action='store_true',
        help="Saves a special requeue script which is designed to "
        "terminate gracefully and automatically restart, filling gaps in the "
        "SLURM schedule with adaptive submit times specified by the time_min "
        "and time configs arguments. This flag requires the total_time, "
        "time, and time_min all be set in the config."
    )

    slurm.add_argument(
        '--config_path', dest='loaded_config_path',
        default='slurm_config.yaml', type=str, help="SLURM config path"
    )

    req = execute_sp.add_argument_group("required")
    req.add_argument(
        '-P', '--package', type=str, default=None, dest='package',
        help='Name of the package to prime. Packages must be contained in the '
        '`package_dir` directory.', required=True
    )

    # Quick post processing on the value for beta_critical
    args = ap.parse_args(sys_argv)

    return args
