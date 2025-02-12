""" SwitchSim Command Line Interface

"""

# --------------------------------------------------
#   Imports
# --------------------------------------------------

import argparse

from switchsim import *


# --------------------------------------------------
#   Functions
# --------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="SwitchSim CLI")
    subparsers = parser.add_subparsers(title="commands", dest="command", required=True)

    # Run simulation Command
    run_simulation_parser = subparsers.add_parser("run-simulation", help="Execute a simulation from a config file")
    run_simulation_parser.add_argument("--type", required=True, choices=["dpt", "buck"], help="Type of simulation to run")
    run_simulation_parser.add_argument("--config-path", required=True, help="File path to simulation config")
    run_simulation_parser.add_argument("--output-path", required=True, help="Directory path to store simulation output data")
    run_simulation_parser.add_argument("--verbose", action="store_true", help="Enable verbose mode")
    run_simulation_parser.set_defaults(func=run_simulation_command)

    # Pull Tracking Data Command
    process_output_parser = subparsers.add_parser("process-output", help="Pull driver tracking data")
    process_output_parser.add_argument("--type", required=True, choices=["dpt", "buck"], help="Type of simulation whose outputs are processed")
    process_output_parser.add_argument("--config-path", required=True, help="File path to simulation config")
    process_output_parser.add_argument("--output-path", required=True, help="Directory path that stored the simulation output data")
    process_output_parser.add_argument("--results-path", required=True, help="Directory path to store simulation processed result data")
    process_output_parser.add_argument("--verbose", action="store_true", help="Enable verbose mode")
    process_output_parser.set_defaults(func=process_output_command)

    args = parser.parse_args()
    args.func(args)


def run_simulation_command(args) -> None:
    simulation_type = SimulationType(args.type)
    config_path = args.config_path
    output_path = args.output_path
    verbose = args.verbose

    config = load_config_from_yaml(
        config_file_path=config_path,
        simulation_type=simulation_type,
    )

    per_run_outputs = run_double_pulse_test_simulations(
        runs=config.runs,
        default_parameters=config.setup.default_parameters,
        output_field_mapping=config.setup.output_field_mapping,
        ltspice_executable_file_path=config.setup.ltspice_executable_file_path,
        verbose=verbose,
    )

    save_simulation_outputs(
        output_directory_path=output_path,
        per_run_outputs=per_run_outputs,
    )


def process_output_command(args) -> None:
    simulation_type = args.type
    config_path = args.config_path
    output_path = args.output_path
    results_path = args.results_path
    verbose = args.verbose

    config = load_config_from_yaml(
        config_file_path=config_path,
        simulation_type=simulation_type,
    )

    per_run_outputs = load_double_pulse_test_simulation_outputs(
        output_directory_path=output_path,
    )

    per_run_results = process_double_pulse_simulation_outputs(
        per_run_outputs=per_run_outputs,
        selected_results=config.results,
    )

    save_simulation_results(
        per_run_results=per_run_results,
        output_directory_path=results_path,
    )


# --------------------------------------------------
#   Entry Point
# --------------------------------------------------

if __name__ == '__main__':
    main()
