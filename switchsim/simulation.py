""" Simulation Module

"""

# --------------------------------------------------
#   Imports
# --------------------------------------------------

import json
import time
import typing
import uuid
import dataclasses
from pathlib import Path
from datetime import datetime

import numpy as np
import yaml
from argon2 import Parameters

from .analysis import *
from .config import *
from .utils import *


# --------------------------------------------------
#   Exports
# --------------------------------------------------


# --------------------------------------------------
#   Constants
# --------------------------------------------------

SIMULATION_PARAMETERS_FILE_NAME = "parameters.json"
SIMULATION_OUTPUT_FILE_NAME = "output.csv"
PARAMETER_SWEEP_FILE_NAME = "results.csv"


# --------------------------------------------------
#   Dataclasses
# --------------------------------------------------

@dataclasses.dataclass(frozen=True)
class SweptParameterData:
    start: float
    end: float
    step: float


@dataclasses.dataclass(frozen=True)
class RunData:
    source_file_path: Path
    parameters_to_sweep: dict[str, SweptParameterData] | None = None


@dataclasses.dataclass(frozen=True)
class ConfigSetupData:
    output_field_mapping: DoublePulseTestOutputFields | BuckConverterOutputFields
    default_parameters: DoublePulseTestParameters | BuckConverterParameters
    ltspice_executable_file_path: str | None = None


@dataclasses.dataclass(frozen=True)
class ConfigData:
    setup: ConfigSetupData
    runs: dict[str, RunData]
    results: list[str]


# --------------------------------------------------
#   Functions
# --------------------------------------------------

def load_config_from_yaml(config_file_path: str, simulation_type: SimulationType) -> ConfigData:
    with open(config_file_path, "r") as file:
        config_data = yaml.safe_load(file)

    return config_from_dict(config_data, simulation_type)


def config_from_dict(config_data: dict, simulation_type: SimulationType) -> ConfigData:
    setup_data = config_data["setup"]
    assert isinstance(setup_data, dict)

    runs_data = config_data["runs"]
    assert isinstance(runs_data, dict)

    results_data = config_data["results"]
    assert isinstance(results_data, list)

    ltspice_executable_file_path = setup_data.get("ltspice_executable_file_path", DEFAULT_LTSPICE_EXECUTABLE_FILE_PATH)

    output_field_mapping_data = setup_data["output_field_mapping"]
    output_field_mapping = _output_field_mapping_from_dict(
        output_field_mapping_data=output_field_mapping_data,
        output_field_mapping_type=get_output_fields_type(simulation_type),
    )

    default_parameters_data = setup_data["default_parameters"]
    default_parameters = _parameters_from_dict(
        parameters_data=default_parameters_data,
        parameters_type=get_parameters_type(simulation_type),
    )

    runs = {run_name: _run_data_from_dict(run_data) for run_name, run_data in runs_data.items()}

    config = ConfigData(
        setup=ConfigSetupData(
            output_field_mapping=output_field_mapping,
            default_parameters=default_parameters,
            ltspice_executable_file_path=ltspice_executable_file_path,
        ),
        runs=runs,
        results=results_data,
    )

    return config


def run_simulations(
        simulation_type: SimulationType,
        runs: dict[str, RunData],
        default_parameters: DoublePulseTestParameters,
        output_field_mapping: DoublePulseTestOutputFields,
        ltspice_executable_file_path: str = DEFAULT_LTSPICE_EXECUTABLE_FILE_PATH,
        verbose: bool = False,
) -> dict[str, dict[str, list[tuple[DoublePulseTestParameters, pd.DataFrame]]]]:
    per_run_outputs = {}
    num_runs = len(runs)

    for i, (run_name, run_data) in enumerate(runs.items()):

        source_file_path = run_data.source_file_path
        parameters_to_sweep = run_data.parameters_to_sweep
        per_parameter_outputs = {}

        verbose_print(verbose, f"Run {i + 1} / {num_runs} - {run_name}: {source_file_path}")

        if parameters_to_sweep is None:
            input_parameters_collection = [default_parameters]
            parameter_outputs = simulate(
                simulation_type=simulation_type,
                source_file_path=source_file_path,
                output_field_mapping=output_field_mapping,
                input_parameters_collection=input_parameters_collection,
                cleanup=True,
                ltspice_executable_file_path=ltspice_executable_file_path,
            )
            per_parameter_outputs["default"] = parameter_outputs

            output_data = parameter_outputs[0]
            num_output_rows = len(output_data)
            verbose_print(verbose, f"\t - default: {num_output_rows} rows")
        else:
            for swept_parameter, swept_parameter_data in parameters_to_sweep.items():
                parameter_outputs = simulate_swept(
                    simulation_type=simulation_type,
                    source_file_path=str(source_file_path),
                    output_field_mapping=output_field_mapping,
                    default_parameters=default_parameters,
                    swept_parameter=swept_parameter,
                    start_value=swept_parameter_data.start,
                    end_value=swept_parameter_data.end,
                    step=swept_parameter_data.step,
                    cleanup=True,
                    ltspice_executable_file_path=ltspice_executable_file_path,
                    verbose=verbose,
                )

                per_parameter_outputs[swept_parameter] = parameter_outputs

                output_data = parameter_outputs[0]
                num_output_rows = len(output_data)
                verbose_print(verbose, f"\t - {swept_parameter}: {num_output_rows} rows")

        per_run_outputs[run_name] = per_parameter_outputs

    return per_run_outputs


def run_double_pulse_test_simulations(
        runs: dict[str, RunData],
        default_parameters: DoublePulseTestParameters,
        output_field_mapping: DoublePulseTestOutputFields,
        ltspice_executable_file_path: str = DEFAULT_LTSPICE_EXECUTABLE_FILE_PATH,
        verbose: bool = False,
) -> dict[str, dict[str, list[tuple[DoublePulseTestParameters, pd.DataFrame]]]]:
    return run_simulations(
        simulation_type=SimulationType.DOUBLE_PULSE_TEST,
        runs=runs,
        default_parameters=default_parameters,
        output_field_mapping=output_field_mapping,
        ltspice_executable_file_path=ltspice_executable_file_path,
        verbose=verbose,
    )


def process_simulation_outputs(
        per_run_outputs: dict[str, dict[str, list[tuple[ParametersType, pd.DataFrame]]]],
        selected_results: list[str],
        simulation_type: SimulationType,
) -> dict[str, dict[str, pd.DataFrame]]:
    # Ensure each item is only represented once
    selected_results = list(set(selected_results))

    per_run_results: dict[str, dict[str, pd.DataFrame]] = {}
    for run_name, per_parameter_outputs in per_run_outputs.items():
        per_parameter_results = {}

        for swept_parameter, parameter_outputs in per_parameter_outputs.items():
            per_parameter_results[swept_parameter] = []

            for input_parameters, output_data in parameter_outputs:
                parameter_results = dataclasses.asdict(input_parameters)
                for result_key in selected_results:
                    getter = simulation_type_result_getters[simulation_type.value][result_key]
                    result = getter(
                        input_data=output_data,
                        input_parameters=input_parameters,
                    )
                    parameter_results[result_key] = result

                per_parameter_results[swept_parameter].append(parameter_results)

            per_parameter_results[swept_parameter] = pd.DataFrame(per_parameter_results[swept_parameter])

        per_run_results[run_name] = per_parameter_results

    return per_run_results


def process_double_pulse_simulation_outputs(
        per_run_outputs: dict[str, dict[str, list[tuple[ParametersType, pd.DataFrame]]]],
        selected_results: list[str],
) -> dict[str, dict[str, pd.DataFrame]]:
    return process_simulation_outputs(
        per_run_outputs=per_run_outputs,
        selected_results=selected_results,
        simulation_type=SimulationType.DOUBLE_PULSE_TEST,
    )


def save_simulation_outputs(
        output_directory_path: str | Path,
        per_run_outputs: dict[str, dict[str, list[tuple[ParametersType, pd.DataFrame]]]]
) -> None:
    if isinstance(output_directory_path, str):
        output_directory_path = Path(output_directory_path)

    output_directory_path.mkdir(parents=True, exist_ok=True)

    for run_name, per_run_outputs in per_run_outputs.items():
        for swept_parameter, per_parameters_outputs in per_run_outputs.items():
            parameters_output_directory_path = output_directory_path / run_name / swept_parameter
            parameters_output_directory_path.mkdir(parents=True, exist_ok=True)

            for i, (used_parameters, simulation_outputs) in enumerate(per_parameters_outputs):
                simulation_directory_path = parameters_output_directory_path / f"{i}"
                simulation_directory_path.mkdir(parents=True, exist_ok=True)

                # Save the used parameters as json
                simulation_parameters_file_path = simulation_directory_path / SIMULATION_PARAMETERS_FILE_NAME
                simulation_parameters_data = dataclasses.asdict(used_parameters)
                with open(str(simulation_parameters_file_path), "w") as json_file:
                    json.dump(simulation_parameters_data, json_file, indent=4)

                # Save the simulation output as csv
                simulation_output_file_path = simulation_directory_path / SIMULATION_OUTPUT_FILE_NAME
                simulation_outputs.to_csv(simulation_output_file_path, index=False)


def load_simulation_outputs(
        simulation_type: SimulationType,
        output_directory_path: str | Path,
) -> dict[str, dict[str, list[tuple[DoublePulseTestParameters, pd.DataFrame]]]]:
    if isinstance(output_directory_path, str):
        output_directory_path = Path(output_directory_path)

    parameters_type = get_parameters_type(simulation_type)

    per_run_outputs = {}

    for run_name in output_directory_path.iterdir():
        if not run_name.is_dir():
            continue
        per_run_outputs[run_name.name] = {}

        for swept_parameter in run_name.iterdir():
            if not swept_parameter.is_dir():
                continue
            per_run_outputs[run_name.name][swept_parameter.name] = []

            for simulation_directory in sorted(swept_parameter.iterdir(), key=lambda x: int(x.name)):
                if not simulation_directory.is_dir():
                    continue

                # Load the simulation parameters
                simulation_parameters_file_path = simulation_directory / SIMULATION_PARAMETERS_FILE_NAME
                with open(simulation_parameters_file_path, "r") as json_file:
                    simulation_parameters_data = json.load(json_file)
                used_parameters = parameters_type(**simulation_parameters_data)

                # Load the simulation outputs
                simulation_output_file_path = simulation_directory / SIMULATION_OUTPUT_FILE_NAME
                simulation_outputs = pd.read_csv(simulation_output_file_path)

                per_run_outputs[run_name.name][swept_parameter.name].append((used_parameters, simulation_outputs))

    return per_run_outputs


def load_double_pulse_test_simulation_outputs(
        output_directory_path: str | Path,
) -> dict[str, dict[str, list[tuple[DoublePulseTestParameters, pd.DataFrame]]]]:
    return load_simulation_outputs(
        output_directory_path=output_directory_path,
        simulation_type=SimulationType.DOUBLE_PULSE_TEST,
    )


def save_simulation_results(
        per_run_results: dict[str, dict[str, pd.DataFrame]],
        output_directory_path: str | Path,
) -> None:
    if isinstance(output_directory_path, str):
        output_directory_path = Path(output_directory_path)

    output_directory_path.mkdir(parents=True, exist_ok=True)

    for run_name, per_swept_parameter_results in per_run_results.items():
        run_directory_path = output_directory_path / run_name
        for swept_parameter, parameter_sweep_results in per_swept_parameter_results.items():
            swept_parameter_directory_path = run_directory_path / swept_parameter
            swept_parameter_directory_path.mkdir(parents=True, exist_ok=True)

            parameter_sweep_results_file_path = swept_parameter_directory_path / PARAMETER_SWEEP_FILE_NAME
            parameter_sweep_results.to_csv(str(parameter_sweep_results_file_path), index=False)


def load_simulation_results(
        output_directory_path: str | Path,
) -> dict[str, dict[str, pd.DataFrame]]:
    if isinstance(output_directory_path, str):
        output_directory_path = Path(output_directory_path)

    results_data = {}

    for run_name in output_directory_path.iterdir():
        if not run_name.is_dir():
            continue
        results_data[run_name.name] = {}

        for swept_parameter in run_name.iterdir():
            if not swept_parameter.is_dir():
                continue

            parameter_sweep_results_file_path = swept_parameter / PARAMETER_SWEEP_FILE_NAME
            if parameter_sweep_results_file_path.exists():
                results_data[run_name.name][swept_parameter.name] = pd.read_csv(parameter_sweep_results_file_path)

    return results_data


def simulate(
        simulation_type: SimulationType,
        source_file_path: str | Path,
        output_field_mapping: OutputFieldsType,
        input_parameters_collection: list[ParametersType],
        cleanup: bool = True,
        ltspice_executable_file_path: str = DEFAULT_LTSPICE_EXECUTABLE_FILE_PATH,
        verbose: bool = False,
) -> list[tuple[DoublePulseTestParameters, pd.DataFrame]]:
    if isinstance(source_file_path, str):
        source_file_path = Path(source_file_path)

    base_directory = source_file_path.parent

    results = []

    num_parameter_sets = len(input_parameters_collection)
    for i, input_parameters in enumerate(input_parameters_collection):
        workspace_simulation_file_name = _generate_simulation_file_name()
        workspace_simulation_file_path = base_directory / f"{workspace_simulation_file_name}.asc"

        # Modify the SPICE file's parameters and save to a new file within the workspace__
        modify_ltspice_params(
            source_file_path=str(source_file_path),
            destination_file_path=str(workspace_simulation_file_path),
            params_to_modify=dataclass_to_dict(input_parameters),
        )

        # Execute the simulation
        verbose_print(verbose, f"\t\t - {i + 1} / {num_parameter_sets} Executing {workspace_simulation_file_path.name}...")
        start_time = time.time()
        execute_ltspice(
            executable_file_path=ltspice_executable_file_path,
            simulation_file_path=str(workspace_simulation_file_path),
        )
        duration = time.time() - start_time
        verbose_print(verbose, f"\t\t - {i + 1} / {num_parameter_sets} Executed in {duration: .2f} seconds")

        # Read and standardise the raw waveform data
        workspace_raw_waveform_file_path = get_raw_file_path(workspace_simulation_file_path)
        # TODO: I HATE coding, why does this work
        # if not workspace_raw_waveform_file_path.exists():
        #     execute_ltspice(
        #         executable_file_path=ltspice_executable_file_path,
        #         simulation_file_path=str(workspace_simulation_file_path),
        #     )

        if not workspace_raw_waveform_file_path.exists():
            raise RuntimeError(f"An error occurred while trying to execute: {source_file_path}")

        waveform_data = read_ltspice_output(
            simulation_type=simulation_type,
            raw_waveform_file_path=str(workspace_raw_waveform_file_path),
            field_mapping=output_field_mapping,
        )

        results.append((input_parameters, waveform_data))

        # CLean up if needed
        if cleanup:
            delete_files_with_same_name(
                directory=base_directory,
                file_name=workspace_simulation_file_path.stem,
            )

    return results


def simulate_double_pulse_test(
        source_file_path: str | Path,
        output_field_mapping: DoublePulseTestOutputFields,
        input_parameters_collection: list[DoublePulseTestParameters],
        cleanup: bool = True,
        ltspice_executable_file_path: str = DEFAULT_LTSPICE_EXECUTABLE_FILE_PATH,
        verbose: bool = False,
) -> list[tuple[DoublePulseTestParameters, pd.DataFrame]]:
    return simulate(
        simulation_type=SimulationType.DOUBLE_PULSE_TEST,
        source_file_path=source_file_path,
        output_field_mapping=output_field_mapping,
        input_parameters_collection=input_parameters_collection,
        cleanup=cleanup,
        ltspice_executable_file_path=ltspice_executable_file_path,
        verbose=verbose,

    )


def simulate_swept(
        simulation_type: SimulationType,
        source_file_path: str,
        output_field_mapping: OutputFieldsType,
        default_parameters: ParametersType,
        swept_parameter: str,
        start_value: float,
        end_value: float,
        step: float,
        cleanup: bool = True,
        ltspice_executable_file_path: str = DEFAULT_LTSPICE_EXECUTABLE_FILE_PATH,
        verbose: bool = False,
) -> list[tuple[ParametersType, pd.DataFrame]]:
    return simulate(
        simulation_type=simulation_type,
        source_file_path=source_file_path,
        output_field_mapping=output_field_mapping,
        input_parameters_collection=_get_swept_parameters(
            default_parameters=default_parameters,
            parameters_type=get_parameters_type(simulation_type),
            swept_parameter=swept_parameter,
            start_value=start_value,
            end_value=end_value,
            step=step,
        ),
        cleanup=cleanup,
        ltspice_executable_file_path=ltspice_executable_file_path,
        verbose=verbose,
    )


def run_buck_converter_simulations(

) -> None:
    pass


def _get_swept_parameters(
        default_parameters: ParametersType,
        parameters_type: type[ParametersType],
        swept_parameter: str,
        start_value: float,
        end_value: float,
        step: float,
) -> list[DoublePulseTestParameters]:
    parameters_collection = []
    for value in np.arange(start_value, end_value, step):
        parameters_dict = dataclasses.asdict(default_parameters)
        parameters_dict[swept_parameter] = value
        parameters_collection.append(parameters_type(**parameters_dict))
    return parameters_collection


def _generate_simulation_file_name(prefix: str | None = None) -> str:
    # Generate a timestamp and UUID
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{prefix + '_' if prefix is not None else ''}{timestamp}_{uuid.uuid4()}"


def _output_field_mapping_from_dict(
        output_field_mapping_data: dict[str, typing.Any],
        output_field_mapping_type,
) -> DoublePulseTestOutputFields | BuckConverterOutputFields:
    output_field_mapping = output_field_mapping_type(
        **output_field_mapping_data,
    )
    return output_field_mapping


def _parameters_from_dict(
        parameters_data: dict[str, typing.Any],
        parameters_type,
) -> DoublePulseTestParameters | BuckConverterParameters:
    parameters = parameters_type(
        **{key: float(value) for key, value in parameters_data.items()},
    )
    return parameters


def _run_data_from_dict(
        run_data: dict[str, typing.Any],
) -> RunData:
    assert isinstance(run_data, dict)
    source_file_path = run_data["source_file_path"]

    if isinstance(source_file_path, str):
        source_file_path = Path(source_file_path)

    parameters_to_sweep_data = run_data.get("parameters_to_sweep")
    parameters_to_sweep = None
    if parameters_to_sweep_data is not None:
        assert isinstance(parameters_to_sweep_data, dict)
        parameters_to_sweep = {
            swept_parameter: SweptParameterData(
                **{key: float(value) for key, value in swept_parameter_data.items()}
            )
            for swept_parameter, swept_parameter_data in parameters_to_sweep_data.items()
        }

    return RunData(
        source_file_path=source_file_path,
        parameters_to_sweep=parameters_to_sweep,
    )
