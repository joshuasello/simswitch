""" Auto GaN Evaluator Script

"""

# --------------------------------------------------
#   Imports
# --------------------------------------------------

import os
import ltspice
import subprocess
import dataclasses
import pandas as pd
import matplotlib.pyplot as plt

from typing import Any


# --------------------------------------------------
#   Exports
# --------------------------------------------------

__all__ = [
    "SubplotData",
    "DoublePulseTestSimulationParameters",
    "DoublePulseTestOutputFields",
    "DoublePulseTestResult",
    "run_double_pulse_simulation",
    "format_simulation_output",
    "energy_between_period",
    "static_drain_source_resistance_between_period",
    "filter_between_period",
    "filter_from_time",
    "modify_asc_params",
    "process_simulation_output",
    "plot_vertical_subplots",
    "plot_drain_source_resistance",
]


# --------------------------------------------------
#   Constants
# --------------------------------------------------

LTSPICE_PATH = "C:\\Users\\joshu\\AppData\\Local\\Programs\\ADI\\LTspice\\LTspice.exe"


# --------------------------------------------------
#   Data Classes
# --------------------------------------------------

@dataclasses.dataclass(frozen=True)
class SubplotData:
    title: str
    label: str
    ylabel: str
    color: str
    xdata: pd.Series
    ydata: pd.Series
    xlabel: str | None = None


@dataclasses.dataclass(frozen=True)
class DoublePulseTestSimulationParameters:
    dc_link_voltage: float
    load_current: float
    first_pulse_start_time: float
    first_pulse_on_time: float
    second_pulse_on_time: float
    dead_time: float
    on_gate_resistance: float
    dut_case_temperature: float


@dataclasses.dataclass(frozen=True)
class DoublePulseTestOutputFields:
    time: str = "time"
    dut_drain_voltage: str = "dut_drain_voltage"
    dut_drain_current: str = "dut_drain_current"
    dut_gate_voltage: str = "dut_gate_voltage"
    dut_source_voltage: str = "dut_source_voltage"


@dataclasses.dataclass(frozen=True)
class DoublePulseTestResult:
    turn_on_energy_loss: float
    turn_off_energy_loss: float
    static_drain_source_resistance: float


# --------------------------------------------------
#   Functions
# --------------------------------------------------

def run_double_pulse_simulation(
        source_ltspice_file_path: str,
        simulation_parameters: DoublePulseTestSimulationParameters,
        output_fields: DoublePulseTestOutputFields,
) -> pd.DataFrame:
    base_directory_path = os.path.dirname(source_ltspice_file_path)
    ltspice_filename = os.path.basename(source_ltspice_file_path)
    temp_ltspice_filename = f"temp_{ltspice_filename}"
    temp_ltspice_file_path = os.path.join(base_directory_path, temp_ltspice_filename)
    temp_raw_file_path = os.path.splitext(temp_ltspice_file_path)[0] + ".raw"
    ltspice_output_filename = os.path.splitext(source_ltspice_file_path)[0] + ".csv"

    modify_asc_params(
        source_ltspice_file_path,
        temp_ltspice_file_path,
        {
            "dc_link_voltage": simulation_parameters.dc_link_voltage,
            "load_current": simulation_parameters.load_current,
            "p1_on_start_time": simulation_parameters.first_pulse_start_time,
            "p1_on_time": simulation_parameters.first_pulse_on_time,
            "p2_on_time": simulation_parameters.second_pulse_on_time,
            "dead_time": simulation_parameters.dead_time,
            "on_gate_resistance": simulation_parameters.on_gate_resistance,
            "dut_case_temperature": simulation_parameters.dut_case_temperature,
        }
    )

    # Run LTspice simulation
    subprocess.call(f'"{LTSPICE_PATH}" -Run -b "{temp_ltspice_file_path}"')

    # Parse the .raw file
    l = ltspice.Ltspice(temp_raw_file_path)
    l.parse()

    # Create a dictionary to store waveforms
    waveform_data = {}

    # Extract waveforms
    for node in l.getVariableNames():
        # print(f"Node: {node}")
        waveform_data[node] = l.get_data(node)

    # Convert dictionary to Pandas DataFrame
    raw_simulation_output = pd.DataFrame(waveform_data)

    formatted_simulation_output = format_simulation_output(
        input_data=raw_simulation_output,
        input_fields=output_fields,
    )

    formatted_simulation_output.to_csv(ltspice_output_filename, index=False)

    return formatted_simulation_output


def format_simulation_output(
        input_data: pd.DataFrame,
        input_fields: DoublePulseTestOutputFields,
) -> pd.DataFrame:
    input_data = input_data.copy()
    formatted_data = input_data.rename(columns={
        input_fields.time: "time",
        input_fields.dut_drain_voltage: "dut_drain_voltage",
        input_fields.dut_drain_current: "dut_drain_current",
        input_fields.dut_gate_voltage: "dut_gate_voltage",
        input_fields.dut_source_voltage: "dut_source_voltage",
    })
    formatted_data = formatted_data[
        ["time", "dut_drain_voltage", "dut_drain_current", "dut_gate_voltage", "dut_source_voltage"]]

    # Add auxiliary fields
    formatted_data["time_differentials"] = formatted_data["time"].diff().fillna(0)
    formatted_data["dut_drain_source_voltage"] = abs(formatted_data["dut_drain_voltage"] - formatted_data[
        "dut_source_voltage"])
    formatted_data["dut_drain_source_power"] = formatted_data["dut_drain_source_voltage"] * formatted_data[
        "dut_drain_current"]
    formatted_data["dut_drain_source_energy"] = formatted_data['dut_drain_source_power'] * formatted_data[
        'time_differentials']
    formatted_data["dut_drain_source_resistance"] = abs(
        formatted_data["dut_drain_source_voltage"] / formatted_data['dut_drain_current'])

    return formatted_data


def energy_between_period(
        simulation_data: pd.DataFrame,
        start_time: float,
        end_time: float,
) -> float:
    # Filter the rows based on the time range
    filtered_data = filter_between_period(simulation_data, start_time, end_time)
    # Sum up the power integral to get the total energy
    total_energy = filtered_data['dut_drain_source_energy'].sum()
    return total_energy


def static_drain_source_resistance_between_period(
        simulation_data: pd.DataFrame,
        start_time: float,
        end_time: float,
) -> float:
    filtered_data = filter_between_period(simulation_data, start_time, end_time)
    static_drain_source_resistance = filtered_data['dut_drain_source_resistance'].mean()
    return static_drain_source_resistance


def filter_between_period(
        input_data: pd.DataFrame,
        start_time: float,
        end_time: float,
) -> pd.DataFrame:
    filtered_data = input_data[(start_time <= input_data['time']) & (input_data['time'] <= end_time)]
    return filtered_data


def filter_from_time(
        input_data: pd.DataFrame,
        start_time: float,
) -> pd.DataFrame:
    filtered_data = input_data[(start_time <= input_data["time"])]
    return filtered_data


def modify_asc_params(
        template_file_path: str,
        output_file_path: str,
        params_to_modify: dict[str, Any],
) -> None:
    with open(template_file_path, 'r') as file:
        lines = file.readlines()

    # Find the line containing the parameters
    for i, line in enumerate(lines):
        if line.strip().startswith("TEXT") and "!.param" in line:
            metadata_segment, params_segment = line.split("!", maxsplit=1)
            param_line = f"{metadata_segment}!"
            param_segments = params_segment.split(r'\n')
            new_param_segments = [
                _modify_param_segment(params_segment, params_to_modify) for params_segment in param_segments
            ]
            param_line += r'\n'.join(new_param_segments)

            lines[i] = param_line
            break

    # Write the modified lines back to the file
    with open(output_file_path, 'w+', encoding='utf-8') as file:
        file.write("".join(lines))


def process_simulation_output(
        simulation_output: pd.DataFrame,
        simulation_parameters: DoublePulseTestSimulationParameters,
) -> DoublePulseTestResult:
    settling_duration = simulation_parameters.dead_time / 2
    turn_off_start_time = simulation_parameters.first_pulse_start_time + 0.5 * simulation_parameters.first_pulse_on_time
    turn_off_end_time = simulation_parameters.first_pulse_start_time + simulation_parameters.first_pulse_on_time + 0.5 * simulation_parameters.dead_time
    print(turn_off_start_time, turn_off_end_time)
    turn_off_energy_loss = energy_between_period(
        simulation_data=simulation_output,
        start_time=turn_off_start_time,
        end_time=turn_off_end_time,
    )
    filtered_data = filter_between_period(
        simulation_output,
        start_time=turn_off_start_time,
        end_time=turn_off_end_time,
    )
    plot_vertical_subplots(
        [
            SubplotData(
                title="turn off",
                label="a",
                ylabel="y",
                color="red",
                xdata=filtered_data["time"],
                ydata=filtered_data["dut_gate_voltage"],
            ),
            SubplotData(
                title="turn off",
                label="a",
                ylabel="y",
                color="blue",
                xdata=filtered_data["time"],
                ydata=filtered_data["dut_drain_source_energy"],
            )
        ]
    )

    turn_on_start_time = simulation_parameters.first_pulse_start_time + simulation_parameters.first_pulse_on_time + 0.5 * simulation_parameters.dead_time
    turn_on_end_time = simulation_parameters.first_pulse_start_time + simulation_parameters.first_pulse_on_time + simulation_parameters.dead_time + 0.5 * simulation_parameters.second_pulse_on_time
    turn_on_energy_loss = energy_between_period(
        simulation_data=simulation_output,
        start_time=turn_on_start_time,
        end_time=turn_on_end_time,
    )
    filtered_data = filter_between_period(
        simulation_output,
        start_time=turn_on_start_time,
        end_time=turn_on_end_time,
    )
    plot_vertical_subplots(
        [
            SubplotData(
                title="turn ON",
                label="a",
                ylabel="y",
                color="red",
                xdata=filtered_data["time"],
                ydata=filtered_data["dut_gate_voltage"],
            ),
            SubplotData(
                title="turn ON",
                label="a",
                ylabel="y",
                color="blue",
                xdata=filtered_data["time"],
                ydata=filtered_data["dut_drain_source_energy"],
            )
        ]
    )
    static_drain_source_resistance = static_drain_source_resistance_between_period(
        simulation_data=simulation_output,
        start_time=simulation_parameters.first_pulse_start_time + settling_duration,
        end_time=simulation_parameters.first_pulse_start_time + simulation_parameters.first_pulse_on_time,
    )

    return DoublePulseTestResult(
        turn_off_energy_loss=turn_off_energy_loss,
        turn_on_energy_loss=turn_on_energy_loss,
        static_drain_source_resistance=static_drain_source_resistance,
    )


def plot_vertical_subplots(
        subplots_data: list[SubplotData],
) -> None:
    if len(subplots_data) != 2:
        raise NotImplementedError()

    fig, ax = plt.subplots(2, 1, figsize=(10, 10), sharex=True)
    for i, subplot_data in enumerate(subplots_data):
        ax[i].plot(
            subplot_data.xdata,
            subplot_data.ydata,
            label=subplot_data.label,
            color=subplot_data.color,
        )
        ax[i].set_title(subplot_data.title)
        if subplot_data.xlabel is not None:
            ax[i].set_xlabel(subplot_data.xlabel)
        ax[i].set_ylabel(subplot_data.ylabel)
        ax[i].grid(True)
        ax[i].legend()

    # Adjust layout
    plt.tight_layout()
    plt.show()


def plot_drain_source_resistance(
        simulation_output: pd.DataFrame,
        simulation_parameters: DoublePulseTestSimulationParameters,
) -> None:
    # Print results
    time_data = filter_from_time(
        simulation_output,
        start_time=simulation_parameters.first_pulse_start_time - 1e-6,
    )['time']
    dut_gate_voltage_data = filter_from_time(
        simulation_output,
        start_time=simulation_parameters.first_pulse_start_time - 1e-6,
    )['dut_gate_voltage']
    dut_drain_source_resistance_data = filter_from_time(
        simulation_output,
        start_time=simulation_parameters.first_pulse_start_time - 1e-6,
    )['dut_drain_source_resistance']
    plot_vertical_subplots(
        subplots_data=[
            SubplotData(
                title="Gate Voltage vs Time",
                label="Gate Voltage (Vg)",
                ylabel="Gate Voltage (V)",
                color="blue",
                xdata=time_data,
                ydata=dut_gate_voltage_data,
            ),
            SubplotData(
                title="Drain-Source Resistance vs Time",
                label="Rds (Drain-Source Resistance)",
                ylabel="Drain-Source Resistance (Ohms)",
                color="orange",
                xdata=time_data,
                ydata=dut_drain_source_resistance_data,
                xlabel="Time (s)"
            )
        ]
    )


def _modify_param_segment(
        param_segment: str,
        params_to_modify: dict[str, Any],
) -> str:
    for param, value in params_to_modify.items():
        if param_segment.strip().startswith(f".param {param}"):
            return f".param {param}={value}"
    return param_segment


# --------------------------------------------------
#   Main
# --------------------------------------------------

if __name__ == '__main__':
    pass