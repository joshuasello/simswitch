""" Field Definitions Module

"""

# --------------------------------------------------
#   Constants
# --------------------------------------------------

TIME_FIELD_NAME = "time"
DUT_DRAIN_VOLTAGE_FIELD_NAME = "dut_drain_voltage"
DUT_DRAIN_CURRENT_FIELD_NAME = "dut_drain_current"
DUT_GATE_VOLTAGE_FIELD_NAME = "dut_gate_voltage"
DUT_SOURCE_VOLTAGE_FIELD_NAME = "dut_source_voltage"
TIME_DIFFERENTIALS_FIELD_NAME = "time_differentials"
DUT_DRAIN_SOURCE_VOLTAGE_FIELD_NAME = "dut_drain_source_voltage"
DUT_DRAIN_SOURCE_POWER_FIELD_NAME = "dut_drain_source_power"
DUT_DRAIN_SOURCE_ENERGY_FIELD_NAME = "dut_drain_source_energy"
DUT_DRAIN_SOURCE_RESISTANCE_FIELD_NAME = "dut_drain_source_resistance"

LOAD_NEGATIVE_VOLTAGE_FIELD_NAME = "load_negative_voltage"
LOAD_POSITIVE_VOLTAGE_FIELD_NAME = "load_positive_voltage"
SUPPLY_VOLTAGE_FIELD_NAME = "supply_voltage"
SUPPLY_CURRENT_FIELD_NAME = "supply_current"
LOAD_CURRENT_FIELD_FIELD_NAME = "load_current"
LOAD_VOLTAGE_FIELD_FIELD_NAME = "load_voltage"

STANDARD_DOUBLE_PULSE_TEST_FIELDS = (
    TIME_FIELD_NAME,
    DUT_GATE_VOLTAGE_FIELD_NAME,
    DUT_DRAIN_VOLTAGE_FIELD_NAME,
    DUT_SOURCE_VOLTAGE_FIELD_NAME,
    DUT_DRAIN_CURRENT_FIELD_NAME
)