"""
This file is part of the Extra-P software (http://www.scalasca.org/software/extra-p)

Copyright (c) 2020,
Technische Universitaet Darmstadt, Germany

This software may be modified and distributed under the terms of
a BSD-style license. See the LICENSE file in the base
directory for details.
"""

import argparse
import logging
import os
import sys
from itertools import chain

import extrap
from extrap.fileio.cube_file_reader2 import read_cube_file
from extrap.fileio.extrap3_experiment_reader import read_extrap3_experiment
from extrap.fileio.io_helper import format_output
from extrap.fileio.io_helper import save_output
from extrap.fileio.json_file_reader import read_json_file
from extrap.fileio.talpas_file_reader import read_talpas_file
from extrap.fileio.text_file_reader import read_text_file
from extrap.modelers import multi_parameter
from extrap.modelers import single_parameter
from extrap.modelers.abstract_modeler import MultiParameterModeler
from extrap.modelers.model_generator import ModelGenerator
from extrap.util.options_parser import ModelerOptionsAction, ModelerHelpAction
from extrap.util.options_parser import SINGLE_PARAMETER_MODELER_KEY, SINGLE_PARAMETER_OPTIONS_KEY
from extrap.util.progress_bar import ProgressBar


def main(args=None, prog=None):
    # argparse
    modelers_list = list(set(
        chain(single_parameter.all_modelers.keys(), multi_parameter.all_modelers.keys())))
    parser = argparse.ArgumentParser(prog=prog, description=extrap.__description__)

    parser.add_argument("--log", action="store", dest="log_level", type=str.upper, default='WARNING',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help="set program's log level (default: WARNING)")
    parser.add_argument("--version", action="version", version=extrap.__title__ + " " + extrap.__version__)
    parser.add_argument("--help-options", choices=modelers_list, help="shows help for modeler options",
                        action=ModelerHelpAction)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cube", action="store_true", default=False, dest="cube", help="load data from cube files")
    group.add_argument("--text", action="store_true", default=False, dest="text", help="load data from text files")
    group.add_argument("--talpas", action="store_true", default=False, dest="talpas",
                       help="load data from Talpas data format")
    group.add_argument("--json", action="store_true", default=False, dest="json",
                       help="load data from JSON or JSON Lines file")
    group.add_argument("--extra-p-3", action="store_true", default=False, dest="extrap3",
                       help="load data from Extra-P 3 experiment")

    parser.add_argument("--modeler", action="store", dest="modeler", default='Default',
                        choices=modelers_list, )

    parser.add_argument("--options", dest="modeler_options", default={}, nargs='+', metavar="KEY=VALUE",
                        action=ModelerOptionsAction,
                        help="options for the modelers")

    parser.add_argument("--scaling", action="store", dest="scaling_type", default="weak", choices=["weak", "strong"],
                        help="set weak or strong scaling when loading data from cube files [weak (default), strong]")
    parser.add_argument("--median", action="store_true", dest="median",
                        help="use median values for computation instead of mean values")
    parser.add_argument("--out", action="store", dest="out", help="specify the output path for Extra-P results")
    parser.add_argument("--print", action="store", dest="print_type", default="all",
                        choices=["all", "callpaths", "metrics", "parameters", "functions"],
                        help="set which information should be displayed after modeling [all (default), callpaths, metrics, parameters, functions]")

    parser.add_argument("path", metavar="FILEPATH", type=str, action="store",
                        help="specify a file path for Extra-P to work with")
    arguments = parser.parse_args(args)

    # set log level
    loglevel = logging.getLevelName(arguments.log_level)
    # set output print type
    printtype = arguments.print_type.upper()

    # set log format location etc.
    if loglevel == logging.DEBUG:
        # import warnings
        # warnings.simplefilter('always', DeprecationWarning)
        # check if log file exists and create it if necessary
        # if not os.path.exists("../temp/extrap.log"):
        #    log_file = open("../temp/extrap.log","w")
        #    log_file.close()
        # logging.basicConfig(format="%(levelname)s - %(asctime)s - %(filename)s:%(lineno)s - %(funcName)10s(): %(message)s", level=loglevel, datefmt="%m/%d/%Y %I:%M:%S %p", filename="../temp/extrap.log", filemode="w")
        logging.basicConfig(
            format="%(levelname)s - %(asctime)s - %(filename)s:%(lineno)s - %(funcName)10s(): %(message)s",
            level=loglevel, datefmt="%m/%d/%Y %I:%M:%S %p")
    else:
        logging.basicConfig(
            format="%(levelname)s: %(message)s", level=loglevel)

    # check scaling type
    scaling_type = arguments.scaling_type

    # set use mean or median for computation
    use_median = arguments.median

    # save modeler output to file?
    print_path = None
    if arguments.out is not None:
        print_output = True
        print_path = arguments.out
    else:
        print_output = False

    if arguments.path is not None:
        with ProgressBar(desc='Loading file') as pbar:
            if arguments.cube:
                # load data from cube files
                if os.path.isdir(arguments.path):
                    experiment = read_cube_file(arguments.path, scaling_type)
                else:
                    logging.error("The given path is not valid. It must point to a directory.")
                    sys.exit(1)
            elif os.path.isfile(arguments.path):
                if arguments.text:
                    # load data from text files
                    experiment = read_text_file(arguments.path, pbar)
                elif arguments.talpas:
                    # load data from talpas format
                    experiment = read_talpas_file(arguments.path, pbar)
                elif arguments.json:
                    # load data from json file
                    experiment = read_json_file(arguments.path, pbar)
                elif arguments.extrap3:
                    # load data from Extra-P 3 file
                    experiment = read_extrap3_experiment(arguments.path, pbar)
                else:
                    logging.error("The file format specifier is missing.")
                    sys.exit(1)
            else:
                logging.error("The given file path is not valid.")
                sys.exit(1)

        # TODO: debug code
        experiment.debug()

        # initialize model generator
        model_generator = ModelGenerator(
            experiment, modeler=arguments.modeler, use_median=use_median)

        # apply modeler options
        modeler = model_generator.modeler
        if isinstance(modeler, MultiParameterModeler) and arguments.modeler_options:
            # set single parameter modeler of multi parameter modeler
            single_modeler = arguments.modeler_options[SINGLE_PARAMETER_MODELER_KEY]
            if single_modeler is not None:
                modeler.single_parameter_modeler = single_parameter.all_modelers[single_modeler]()
            # apply options of single parameter modeler
            if modeler.single_parameter_modeler is not None:
                for name, value in arguments.modeler_options[SINGLE_PARAMETER_OPTIONS_KEY].items():
                    if value is not None:
                        setattr(modeler.single_parameter_modeler, name, value)

        for name, value in arguments.modeler_options.items():
            if value is not None:
                setattr(modeler, name, value)

        with ProgressBar(desc='Generating models') as pbar:
            # create models from data
            model_generator.model_all(pbar)

        # format modeler output into text
        text = format_output(experiment, printtype)

        # print formatted output to command line
        print(text)

        # save formatted output to text file
        if print_output:
            save_output(text, print_path)

    else:
        logging.error("No file path given to load files.")
        sys.exit(1)


if __name__ == "__main__":
    main()