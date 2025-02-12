""" SPICE Simulation Handling Module

"""


# --------------------------------------------------
#   Imports
# --------------------------------------------------

import os
import enum
from dataclasses import dataclass

import ltspice
import subprocess
import pandas as pd
import dataclasses
from pathlib import Path

from prompt_toolkit.lexers import SimpleLexer

from .fields import *


# --------------------------------------------------
#   Exports
# --------------------------------------------------

__all__ = [
    "SimulationType",
    "DoublePulseTestParameters",
    "BuckConverterParameters",
    "ParametersType",
    "DoublePulseTestOutputFields",
    "BuckConverterOutputFields",
    "OutputFieldsType",
    "modify_ltspice_params",
    "execute_ltspice",
    "read_ltspice_output",
    "get_raw_file_path",
    "get_parameters_type",
    "get_output_fields_type",
]

# --------------------------------------------------
#   Enums
# --------------------------------------------------

class SimulationType(enum.StrEnum):
    DOUBLE_PULSE_TEST = "dpt"
    BUCK_CONVERTER = "buck"


# --------------------------------------------------
#   Dataclasses
# --------------------------------------------------

@dataclasses.dataclass(frozen=True)
class DoublePulseTestParameters:
    # Stores the time before the first pulse in seconds
    leading_duration: float
    # Stores the time after the second pulse in seconds
    lagging_duration: float
    # Stores the voltage supplied to the load when the DUT is on in volts
    load_supply_voltage: float
    # Stores the value of the current after the completion of the first pulse in amps
    load_test_current: float
    # Stores the duration of the first pulse in seconds
    first_pulse_duration: float
    # Stores the duration of the second pulse in seconds
    second_pulse_duration: float
    # Stores the time between the two pulses in seconds
    off_duration: float
    # Stores the resistance connected to the gate in ohms
    on_gate_resistance: float
    # Stores the case temperature of the device under test (DUT) in Celsius
    dut_case_temperature: float
    # Stores the max time interval for each simulation step
    max_timestep: float = 1e-6

    @property
    def first_pulse_start(self) -> float:
        return self.leading_duration

    @property
    def second_pulse_start(self) -> float:
        return sum([
            self.leading_duration,
            self.first_pulse_duration,
            self.off_duration,
        ])

    @property
    def duration(self) -> float:
        return sum([
            self.second_pulse_start,
            self.second_pulse_duration,
            self.lagging_duration,
        ])

    @property
    def load_inductance(self) -> float:
        return self.load_supply_voltage * self.first_pulse_duration / self.load_test_current


@dataclasses.dataclass(frozen=True)
class BuckConverterParameters:
    # Stores the voltage supplied to the load when the DUT is on in volts
    supply_input_voltage: float
    # Stores the current supplied to the load
    load_current: float
    # Stores the allowable current ripple through the inductor
    current_ripple: float
    # Stores the allowable output voltage ripple over the load
    voltage_ripple: float
    # Stores the case temperature of the device under test (DUT) in Celsius
    dut_case_temperature: float
    # Stores the switching frequency of the DUT
    switching_frequency: float
    # Stores the switching duty-cycle of the DUT
    duty_cycle: float
    # Stores the simulation duration
    duration: float
    # Stores the max time interval for each simulation step
    max_timestep: float = 1e-6

    @property
    def supply_output_voltage(self) -> float:
        return self.duty_cycle * self.supply_input_voltage

    @property
    def series_inductance(self) -> float:
        return (self.supply_input_voltage - self.supply_output_voltage) * self.duty_cycle / (self.current_ripple * self.switching_frequency)

    @property
    def shunt_capacitance(self) -> float:
        return self.current_ripple / (8 * self.switching_frequency * self.voltage_ripple)

    @property
    def load_resistance(self) -> float:
        return self.supply_output_voltage / self.load_current


ParametersType = DoublePulseTestParameters | BuckConverterParameters


@dataclasses.dataclass(frozen=True)
class DoublePulseTestOutputFields:
    time: str | list[str] = TIME_FIELD_NAME
    dut_gate_voltage: str | list[str] = DUT_GATE_VOLTAGE_FIELD_NAME
    dut_drain_voltage: str | list[str] = DUT_DRAIN_VOLTAGE_FIELD_NAME
    dut_source_voltage: str | list[str] = DUT_SOURCE_VOLTAGE_FIELD_NAME
    dut_drain_current: str | list[str] = DUT_DRAIN_CURRENT_FIELD_NAME

    @property
    def standard_fields(self) -> list:
        return list(dataclasses.asdict(self).keys())


@dataclasses.dataclass(frozen=True)
class BuckConverterOutputFields:
    time: str | list[str] = TIME_FIELD_NAME
    dut_gate_voltage: str | list[str] = DUT_GATE_VOLTAGE_FIELD_NAME
    dut_drain_voltage: str | list[str] = DUT_DRAIN_VOLTAGE_FIELD_NAME
    dut_source_voltage: str | list[str] = DUT_SOURCE_VOLTAGE_FIELD_NAME
    supply_current: str | list[str] = SUPPLY_CURRENT_FIELD_NAME
    load_current: str | list[str] = LOAD_CURRENT_FIELD_FIELD_NAME
    load_positive_voltage: str | list[str] = LOAD_POSITIVE_VOLTAGE_FIELD_NAME
    load_negative_voltage: str | list[str] = LOAD_NEGATIVE_VOLTAGE_FIELD_NAME

    @property
    def standard_fields(self) -> list:
        return list(dataclasses.asdict(self).keys())


OutputFieldsType = DoublePulseTestOutputFields | BuckConverterOutputFields


# --------------------------------------------------
#   Functions
# --------------------------------------------------

def modify_ltspice_params(
        source_file_path: str,
        destination_file_path: str,
        params_to_modify: dict[str, float],
) -> None:
    # TODO: Improve this to handle inline param insertions and non-added params
    with open(source_file_path, 'r') as file:
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

            lines[i] = param_line + "\n"
            break

    # Write the modified lines back to the file
    with open(destination_file_path, 'w+', encoding='utf-8') as file:
        file.write("".join(lines))


def execute_ltspice(
        executable_file_path: str,
        simulation_file_path: str,
) -> None:
    if not os.path.exists(executable_file_path):
        raise FileNotFoundError(executable_file_path)
    if not os.path.exists(simulation_file_path):
        raise FileNotFoundError(simulation_file_path)

    subprocess.call(f'"{executable_file_path}" -Run -b "{simulation_file_path}"')


def get_raw_file_path(asc_file_path: str | Path) -> Path:
    if isinstance(asc_file_path, str):
        asc_file_path = Path(asc_file_path)
    raw_file_path = asc_file_path.with_suffix(".raw")
    return raw_file_path


def get_parameters_type(simulation_type: SimulationType) -> type[ParametersType]:
    return _parameters_types[simulation_type.value]


def get_output_fields_type(simulation_type: SimulationType) -> type[OutputFieldsType]:
    return _output_field_types[simulation_type.value]


def _standardise_waveform_data(
        simulation_type: SimulationType,
        raw_waveform_data: pd.DataFrame,
        field_mapping: OutputFieldsType,
) -> pd.DataFrame:
    standardised_data = _renamed_columns_waveform_data(
        waveform_data=raw_waveform_data,
        field_mapping=field_mapping,
    )

    # If the source voltage column does not exist in the data, LTSpice has assigned it ground
    # with zero voltage. This should be added manually in this case.
    if DUT_SOURCE_VOLTAGE_FIELD_NAME not in standardised_data.columns:
        standardised_data[DUT_SOURCE_VOLTAGE_FIELD_NAME] = 0.0

    # Filter the dataset to only contained the required fields
    # standardised_data = standardised_data[list(STANDARD_DOUBLE_PULSE_TEST_FIELDS)]
    standardised_data = _filtered_columns_waveform_data(
        waveform_data=standardised_data,
        field_mapping=field_mapping,
    )

    # Add auxiliary fields
    standardised_data = _auxiliary_field_adders[simulation_type.value](
        waveform_data=standardised_data,
    )

    return standardised_data


def _add_double_pulse_test_auxiliary_fields(
        waveform_data: pd.DataFrame,
) -> pd.DataFrame:
    dut_drain_voltage = waveform_data[DUT_DRAIN_VOLTAGE_FIELD_NAME]
    dut_source_voltage = waveform_data[DUT_SOURCE_VOLTAGE_FIELD_NAME]
    dut_drain_current = waveform_data[DUT_DRAIN_CURRENT_FIELD_NAME]

    waveform_data[TIME_DIFFERENTIALS_FIELD_NAME] = waveform_data[TIME_FIELD_NAME].diff().fillna(0)
    waveform_data[DUT_DRAIN_SOURCE_VOLTAGE_FIELD_NAME] = dut_drain_voltage - dut_source_voltage
    dut_drain_source_voltage = waveform_data[DUT_DRAIN_SOURCE_VOLTAGE_FIELD_NAME]
    waveform_data[DUT_DRAIN_SOURCE_POWER_FIELD_NAME] = dut_drain_source_voltage * dut_drain_current
    waveform_data[DUT_DRAIN_SOURCE_ENERGY_FIELD_NAME] = (
            waveform_data[DUT_DRAIN_SOURCE_POWER_FIELD_NAME] * waveform_data[TIME_DIFFERENTIALS_FIELD_NAME]
    )
    waveform_data[DUT_DRAIN_SOURCE_RESISTANCE_FIELD_NAME] = abs(
        waveform_data[DUT_DRAIN_SOURCE_VOLTAGE_FIELD_NAME] / waveform_data[DUT_DRAIN_CURRENT_FIELD_NAME]
    )

    return waveform_data


def _add_buck_converter_auxiliary_fields(
        waveform_data: pd.DataFrame,
) -> pd.DataFrame:
    waveform_data[SUPPLY_VOLTAGE_FIELD_NAME] = waveform_data[DUT_DRAIN_VOLTAGE_FIELD_NAME] - waveform_data[LOAD_NEGATIVE_VOLTAGE_FIELD_NAME]
    waveform_data[LOAD_VOLTAGE_FIELD_FIELD_NAME] = waveform_data[LOAD_POSITIVE_VOLTAGE_FIELD_NAME] - waveform_data[LOAD_NEGATIVE_VOLTAGE_FIELD_NAME]
    return waveform_data


def read_ltspice_output(
        simulation_type: SimulationType,
        raw_waveform_file_path: str,
        field_mapping: OutputFieldsType,
) -> pd.DataFrame:
    raw_waveform_data = _read_ltspice_waveform(raw_waveform_file_path)

    standardised_data = _standardise_waveform_data(
        simulation_type=simulation_type,
        raw_waveform_data=raw_waveform_data,
        field_mapping=field_mapping
    )

    return standardised_data

def _read_ltspice_waveform(file_path: str) -> pd.DataFrame:
    # Parse the .raw file
    l = ltspice.Ltspice(file_path)
    l.parse()

    waveform_data = {node: l.get_data(node) for node in l.getVariableNames()}

    return pd.DataFrame(waveform_data)


def _modify_param_segment(
        param_segment: str,
        params_to_modify: dict[str, float],
) -> str:
    for param, value in params_to_modify.items():
        if param_segment.strip().startswith(f".param {param}"):
            return f".param {param}={value}"
    return param_segment


def _renamed_columns_waveform_data(
        waveform_data: pd.DataFrame,
        field_mapping: OutputFieldsType,
) -> pd.DataFrame:
    field_mapping: dict = dataclasses.asdict(field_mapping)

    new_columns = {}
    for standard_field, output_field in field_mapping.items():
        if isinstance(output_field, str):
            new_columns[output_field] = standard_field
        elif isinstance(output_field, list):
            for field in output_field:
                if field in waveform_data.columns:
                    new_columns[field] = standard_field
                    break
        else:
            raise TypeError(f"Output field must be a string or a list of strings. Got {type(output_field)}")

    return waveform_data.rename(columns=new_columns)


def _filtered_columns_waveform_data(
        waveform_data: pd.DataFrame,
        field_mapping: OutputFieldsType,
) -> pd.DataFrame:
    try:
        return waveform_data[field_mapping.standard_fields]
    except KeyError:
        missing_columns = set()
        for required_column in field_mapping.standard_fields:
            if required_column not in waveform_data.columns:
                missing_columns.add(required_column)

        raise KeyError(f"Missing columns: {', '.join(missing_columns)} from columns -> [{', '.join(list(waveform_data.columns))}]")


# --------------------------------------------------
#   Variables
# --------------------------------------------------

_parameters_types = {
    SimulationType.DOUBLE_PULSE_TEST.value: DoublePulseTestParameters,
    SimulationType.BUCK_CONVERTER.value: BuckConverterParameters,
}

_output_field_types = {
    SimulationType.DOUBLE_PULSE_TEST.value: DoublePulseTestOutputFields,
    SimulationType.BUCK_CONVERTER.value: BuckConverterOutputFields,
}

_auxiliary_field_adders = {
    SimulationType.DOUBLE_PULSE_TEST.value: _add_double_pulse_test_auxiliary_fields,
    SimulationType.BUCK_CONVERTER.value: _add_buck_converter_auxiliary_fields,
}