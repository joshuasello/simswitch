# **switchsim (beta)**  
*A Python Package for Automating GaN Device Simulations and Analysis*

- Version: beta
- Author: Joshua Sello (In fullfillment of Erasmus+ Exchange)
- Institutions: Reutlingen Hochschule, and Stellenbosch University
- Supervisors: Jannik Maier, and Dr.-Ing. Ertugrul Sönmez
- Lihense: [MIT](LICENSE)

---

### **Description**
**switchsim** is a Python package designed to streamline the simulation  
and analysis of power electronic circuits, with a focus on  
Gallium Nitride (GaN) devices. Built for researchers and engineers,  
the package automates workflows for circuit parameter modification,  
simulation execution, and data extraction, enabling systematic  
evaluation of GaN transistors under various operating conditions.  

The package integrates seamlessly with **LTSpice**, allowing users to:  
- Automate **double pulse tests (DPT)** for evaluating switching losses.  
- Analyze GaN devices in **buck converter topologies** to assess steady-state performance.  
- Conduct **parametric sweeps** over voltage, current, temperature, and gate resistance.  
- Visualize simulation results with clear, customizable plots.  

Included in this repository is an example folder with pre-made circuits to test with. In order to use the examples, 
the config yaml files will need to be adjusted to reflect the local file locations of your circuit.

---

## **Simulation Configuration**  

The **switchsim** package relies on a **YAML configuration file** to define  
the parameters and execution settings for both the **double pulse test (DPT)**  
and other power electronic simulations like the **buck-converter**. Below is a breakdown of how  
to configure and customize your simulations.

### **1. YAML Configuration Structure**  

A typical configuration file (`dpt_gan_simulation.yaml`, for example) looks like this:

```yaml
setup:
  # (Optional) Stores the file path to the LTSpice executable. Defaults to local copy if not specified
  ltspice_executable_file_path: C:\path\to\LTspice.exe

  output_field_mapping:
    time: time
    dut_gate_voltage: V(dut_gate_voltage)
    dut_drain_voltage: V(dut_drain_voltage)
    dut_source_voltage: V(dut_source_voltage)
    dut_drain_current: Ix(dut:DRAININ)

  default_parameters:
    leading_duration: 5e-6
    lagging_duration: 5e-6
    load_supply_voltage: 400
    load_test_current: 4
    first_pulse_duration: 50e-6
    second_pulse_duration: 5e-6
    off_duration: 5e-6
    on_gate_resistance: 10
    dut_case_temperature: 25
    max_timestep: 500e-7

runs:
  double_pulse_test_gan_gs66516t:
    source_file_path: C:\path\to\double_pulse_test_gan_gs66516t.asc
    parameters_to_sweep:
      load_test_current:
        start: 5
        end: 25
        step: 5

results:
  - turn_on_loss
  - turn_off_loss
```

### **2. Available Parameters and Output Field Mapping**  

The **switchsim** package allows users to configure simulations using a
set of predefined parameters for **Double Pulse Test (DPT)** and 
**Buck Converter** simulations. This section details the available 
parameters and output fields that can be mapped to simulation results.  

---

#### **2.1 Double Pulse Test Parameters**  
The **Double Pulse Test (DPT)** configuration defines the operating 
conditions for evaluating the switching characteristics of a 
**Device Under Test (DUT)**.

| Parameter               | Description                                                    | Unit    |
|-------------------------|----------------------------------------------------------------|---------|
| `leading_duration`      | Time before the first pulse starts                             | seconds |
| `lagging_duration`      | Time after the second pulse before simulation ends             | seconds |
| `load_supply_voltage`   | Voltage applied to the load when the DUT is ON                 | volts   |
| `load_test_current`     | Current flowing through the load at the end of the first pulse | amps    |
| `first_pulse_duration`  | Duration of the first switching pulse                          | seconds |
| `second_pulse_duration` | Duration of the second switching pulse                         | seconds |
| `off_duration`          | Time interval between the two pulses                           | seconds |
| `on_gate_resistance`    | Gate resistance used for driving the DUT                       | ohms    |
| `dut_case_temperature`  | Case temperature of the DUT                                    | °C      |
| `max_timestep`          | Maximum allowed time step for simulation                       | seconds |

##### **Derived Properties**  
These properties are automatically calculated from the given parameters:  

| Derived Property     | Description                       | Unit    |
|----------------------|-----------------------------------|---------|
| `first_pulse_start`  | Time when the first pulse starts  | seconds |
| `second_pulse_start` | Time when the second pulse starts | seconds |
| `duration`           | Total simulation duration         | seconds |
| `load_inductance`    | Inductance of the load circuit    | henry   |

---

#### **2.2 Buck Converter Parameters**  
The **Buck Converter** simulation parameters define the behavior of 
a **DC-DC converter**, allowing users to analyze its performance under 
different load and switching conditions.  

| Parameter              | Description                                   | Unit       |
|------------------------|-----------------------------------------------|------------|
| `supply_input_voltage` | Input voltage applied to the buck converter   | volts      |
| `load_current`         | Steady-state current drawn by the load        | amps       |
| `current_ripple`       | Allowed current ripple in the inductor        | amps       |
| `voltage_ripple`       | Allowed output voltage ripple across the load | volts      |
| `dut_case_temperature` | Case temperature of the DUT                   | °C         |
| `switching_frequency`  | Frequency of the switching operation          | Hz         |
| `duty_cycle`           | Duty cycle of the switching waveform          | percentage |
| `duration`             | Total simulation duration                     | seconds    |
| `max_timestep`         | Maximum allowed time step for simulation      | seconds    |

##### **Derived Properties**  
These properties are automatically computed based on the input parameters:

| Derived Property        | Description                                       | Unit   |
|-------------------------|---------------------------------------------------|--------|
| `supply_output_voltage` | Output voltage of the converter                   | volts  |
| `series_inductance`     | Inductance required in the buck converter circuit | henry  |
| `shunt_capacitance`     | Capacitance required for smoothing voltage ripple | farads |
| `load_resistance`       | Resistance of the load                            | ohms   |

---

#### **2.3 Output Field Mapping**  
During a simulation, **LTSpice** generates output signals that are mapped 
to specific variables in **switchsim**. These fields define the expected 
simulation output for **Double Pulse Test** and **Buck Converter** 
simulations.  

##### **Double Pulse Test Output Fields**  
| Field Name           | Description                                  |
|----------------------|----------------------------------------------|
| `time`               | Time variable for the simulation             |
| `dut_gate_voltage`   | Voltage applied to the gate of the DUT       |
| `dut_drain_voltage`  | Voltage at the drain of the DUT              |
| `dut_source_voltage` | Voltage at the source of the DUT             |
| `dut_drain_current`  | Current flowing through the drain of the DUT |

##### **Buck Converter Output Fields**  
| Field Name              | Description                                    |
|-------------------------|------------------------------------------------|
| `time`                  | Time variable for the simulation               |
| `dut_gate_voltage`      | Voltage applied to the gate of the DUT         |
| `dut_drain_voltage`     | Voltage at the drain of the DUT                |
| `dut_source_voltage`    | Voltage at the source of the DUT               |
| `supply_current`        | Current supplied to the buck converter circuit |
| `load_current`          | Current flowing through the load               |
| `load_positive_voltage` | Positive terminal voltage of the load          |
| `load_negative_voltage` | Negative terminal voltage of the load          |

---

#### **2.4 Modifying Output Field Mapping in YAML Configuration**  
The output fields can be customized in the YAML configuration file under 
the `output_field_mapping` section:

```yaml
setup:
  output_field_mapping:
    time: time
    dut_gate_voltage: V(dut_gate_voltage)
    dut_drain_voltage: V(dut_drain_voltage)
    dut_source_voltage: V(dut_source_voltage)
    dut_drain_current: Ix(dut:DRAININ)
```
This ensures that **switchsim** correctly interprets the simulation results from **LTSpice**.

### **3. Configuring the Simulation**  

#### **Setup Section**  
This section defines **global parameters** for the simulation framework, including:
- The path to the **LTSpice executable**.
- The **output field mapping**, ensuring correct parsing of waveform data.

| Parameter                      | Description                                                                                     |
|--------------------------------|-------------------------------------------------------------------------------------------------|
| `ltspice_executable_file_path` | (Optional) Path to the LTSpice executable used for simulations.                                 |
| `output_field_mapping`         | Maps simulation output variables present in the raw LTSpice output data to standardised labels. |

The raw LTSpice output fields can be found at the bottom left of the program window after hovering over a node or port on the circuit. To get current fields, the simulation will need to be running.

#### **Default Parameters**  
These parameters define the default circuit conditions used in the 
simulation:

For example:
| Parameter               | Description                             | Value |
|-------------------------|-----------------------------------------|---------------|
| `leading_duration`      | Duration of the leading pulse (s)       | `5e-6`        |
| `lagging_duration`      | Duration of the lagging pulse (s)       | `5e-6`        |
| `load_supply_voltage`   | Voltage applied to the test circuit (V) | `400`         |
| `load_test_current`     | Current flowing through the circuit (A) | `4`           |
| `first_pulse_duration`  | Length of the first pulse (s)           | `50e-6`       |
| `second_pulse_duration` | Length of the second pulse (s)          | `5e-6`        |
| `off_duration`          | Duration of the off-state (s)           | `5e-6`        |
| `on_gate_resistance`    | Gate drive resistance (Ω)               | `10`          |
| `dut_case_temperature`  | Case temperature of the device (°C)     | `25`          |
| `max_timestep`          | Maximum simulation time step (s)        | `500e-7`      |

When a sweep is performed for a chosen parameter, the value of that parameter is varied for the given range 
while the others remain constant.

#### **Runs Section**  
This section defines **specific test cases**, including:
- The **circuit file** used for simulation.
- **Parameters to sweep** (i.e., variables that change between test runs).

For example, the following YAML entry:
```yaml
runs:
  double_pulse_test_gan_gs66516t:
    source_file_path: C:\path\to\double_pulse_test_gan_gs66516t.asc
    parameters_to_sweep:
      load_test_current:
        start: 5
        end: 25
        step: 5
```
specifies:
- The source circuit file **double_pulse_test_gan_gs66516t.asc**.
- The **load_test_current** is swept from **5A** to **25A** (non-inclusive), increasing in steps of **5A**.

#### **Results Section**  
This section specifies **which results should be extracted** f
rom the simulation:

```yaml
results:
  - turn_on_loss
  - turn_off_loss
```
In this example:
- **turn_on_loss** → Extracts energy loss during transistor turn-on.
- **turn_off_loss** → Extracts energy loss during transistor turn-off.

---

## **4. Running a Simulation**
### **Using the Command-Line Interface (CLI)**  
The **switchsim** package provides a **command-line interface (CLI)**
to run and process power electronics simulations. The CLI supports 
**double pulse test (DPT)** and **buck converter** simulations, 
enabling automated data processing and results extraction.  

### **4.1 Executing a Simulation**  
To run a simulation using a YAML configuration file, use the 
following command:  

```bash
python switchsim/cli.py run-simulation --type=dpt --config-path=dpt_gan_simulation.yaml --output-path=simulation_outputs --verbose
```

### **4.2 Command Breakdown**  
- `run-simulation` → Specifies that a simulation should be executed.  
- `--type` → Defines the type of simulation to run (`dpt` for Double Pulse Test or `buck` for Buck Converter).  
- `--config-path` → Path to the YAML configuration file that defines the simulation parameters.  
- `--output-path` → Directory path where simulation output data will be stored.  
- `--verbose` → Enables detailed logging for debugging and process tracking.  

#### **Example: Running a Buck Converter Simulation**  
```bash
python switchsim.py run-simulation --type=buck --config-path=buck_simulation.yaml --output-path=simulation_outputs --verbose
```

---

### **4.3 Processing Simulation Outputs**  
Once a simulation has been executed, the results can be processed 
using the **process-output** command. This extracts key metrics 
such as **switching losses** and **waveform characteristics**.

#### **Command to Process Simulation Outputs**  
```bash
python switchsim.py process-output --type=dpt --config-path=dpt_gan_simulation.yaml --output-path=simulation_outputs --results-path=simulation_results --verbose
```

### **4.4 Command Breakdown**  
- `process-output` → Specifies that the simulation outputs should be processed and analyzed.  
- `--type` → Defines the type of simulation whose outputs are being processed (`dpt` or `buck`).  
- `--config-path` → Path to the YAML configuration file used during simulation.  
- `--output-path` → Directory containing the raw simulation output data.  
- `--results-path` → Directory where processed results will be stored.  
- `--verbose` → Enables detailed logging during processing.  

#### **Example: Processing Buck Converter Simulation Results**  
```bash
python switchsim.py process-output --type=buck --config-path=buck_simulation.yaml --output-path=simulation_outputs --results-path=processed_results --verbose
```

---

### **4.5 Workflow Overview**  
#### **Step 1: Run a Simulation**
- Configure the **YAML file** (e.g., `dpt_gan_simulation.yaml`).  
- Execute the simulation using `run-simulation`.  
- Output files will be saved in the specified `output-path`.  

#### **Step 2: Process the Results**
- Use `process-output` to extract relevant performance metrics.  
- Processed results will be stored in `results-path`.  

#### **Step 3: Analyze the Data**
- Extracted results can be visualized or further analyzed using Python scripts or plotting tools.  

---

### **4.6 Example Workflow**  

```bash
# Step 1: Run a Double Pulse Test (DPT) simulation
python switchsim/cli.py run-simulation --type=dpt --config-path=dpt_gan_simulation.yaml --output-path=simulation_outputs --verbose

# Step 2: Process the DPT simulation results
python switchsim/cli.py process-output --type=dpt --config-path=dpt_gan_simulation.yaml --output-path=simulation_outputs --results-path=simulation_results --verbose
```

### **Example: Modifying the Simulation**
#### **Changing the Load Supply Voltage**
Modify `load_supply_voltage` in the YAML file:
```yaml
default_parameters:
  load_supply_voltage: 500  # New voltage value
```
Run the simulation again:
```bash
python run_simulation.py --config dpt_gan_simulation.yaml --verbose
```

#### **Sweeping Gate Resistance**
To analyze the effect of **gate resistance** on switching losses, modify:
```yaml
parameters_to_sweep:
  on_gate_resistance:
    start: 5
    end: 20
    step: 5
```
This sweeps **gate resistance** from **5Ω to 20Ω** in steps of **5Ω**.

---

## **To-Do List**
- [X] Implement Double Pulse Test (DPT) parameter injection and analysis.
- [X] Implement DC-DC Buck Converter parameter injection and analysis.
- [X] Command Line Interface (CLI).
- [X] Code documentation.

