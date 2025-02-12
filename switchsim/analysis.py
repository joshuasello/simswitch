""" Analysis Module

"""

# --------------------------------------------------
#   Imports
# --------------------------------------------------

import pandas as pd

from .fields import *
from .spice import *


# --------------------------------------------------
#   Exports
# --------------------------------------------------


# --------------------------------------------------
#   Functions
# --------------------------------------------------

def get_power_efficiency(input_data: pd.DataFrame, input_parameters: BuckConverterParameters) -> float:
    steady_state_data = _filtered_for_steady_state(
        input_data=input_data,
        input_parameters=input_parameters,
    )
    output_power = abs((input_parameters.load_resistance * steady_state_data[LOAD_CURRENT_FIELD_FIELD_NAME]**2).mean())
    input_power = abs((steady_state_data[SUPPLY_VOLTAGE_FIELD_NAME] * steady_state_data[SUPPLY_CURRENT_FIELD_NAME]).mean())

    power_efficiency = output_power / input_power

    print(f"{output_power=} / {input_power=} = {power_efficiency=}")

    return power_efficiency



def _filtered_for_steady_state(input_data: pd.DataFrame, input_parameters: BuckConverterParameters) -> pd.DataFrame:
    # TODO: Fix this: Assume that at the halfway point of the simulation run time, the output has reached stead-state
    start = input_parameters.duration / 2
    end = start + input_parameters.duration / 4
    return input_data[(start <= input_data[TIME_FIELD_NAME]) & (input_data[TIME_FIELD_NAME] <= end)]


def extract_ripple_performance(input_data: pd.DataFrame) -> float:
    raise NotImplementedError()


def get_turn_on_energy_loss(input_data: pd.DataFrame, input_parameters: DoublePulseTestParameters) -> float:
    start_time = input_parameters.second_pulse_start
    end_time = input_parameters.second_pulse_start + 0.5 * input_parameters.second_pulse_duration

    turn_on_energy_loss = get_drain_source_energy_between_period(
        input_data=input_data,
        start_time=start_time,
        end_time=end_time
    )

    return turn_on_energy_loss


def get_turn_off_energy_loss(input_data: pd.DataFrame, input_parameters: DoublePulseTestParameters) -> float:
    start_time = input_parameters.first_pulse_start + input_parameters.first_pulse_duration
    end_time = start_time + 0.5 * input_parameters.off_duration

    turn_off_energy_loss = get_drain_source_energy_between_period(
        input_data=input_data,
        start_time=start_time,
        end_time=end_time
    )

    return turn_off_energy_loss


def get_drain_source_energy_between_period(input_data: pd.DataFrame, start_time: float, end_time: float) -> float:
    filtered_data = get_filtered_between_period(input_data, start_time, end_time)
    total_energy = get_total_drain_source_energy(filtered_data)
    return total_energy


def get_total_drain_source_energy(input_data: pd.DataFrame) -> float:
    total_energy = input_data[DUT_DRAIN_SOURCE_ENERGY_FIELD_NAME].sum()
    return total_energy


def get_filtered_between_period(input_data: pd.DataFrame, start_time: float, end_time: float) -> pd.DataFrame:
    filtered_data = input_data[(start_time <= input_data[TIME_FIELD_NAME]) & (input_data[TIME_FIELD_NAME] <= end_time)]
    return filtered_data


def get_total_drain_source_energy_between_period(
        input_data: pd.DataFrame,
        start_time: float,
        end_time: float,
) -> float:
    filtered_data = get_filtered_between_period(input_data, start_time, end_time)
    total_energy = get_total_drain_source_energy(filtered_data)
    return total_energy


# --------------------------------------------------
#   Variables
# --------------------------------------------------

double_pulse_test_result_getters = {
    "turn_on_loss": get_turn_on_energy_loss,
    "turn_off_loss": get_turn_off_energy_loss,
}

buck_converter_getters = {
    "power_efficiency": get_power_efficiency
}


simulation_type_result_getters = {
    SimulationType.DOUBLE_PULSE_TEST.value: double_pulse_test_result_getters,
    SimulationType.BUCK_CONVERTER.value: buck_converter_getters,
}
