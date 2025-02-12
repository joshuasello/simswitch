""" Visualisations Module

"""

# --------------------------------------------------
#   Imports
# --------------------------------------------------

import itertools
import dataclasses
import pandas as pd
import matplotlib.pyplot as plt


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
class ResultPlotData:
    label: str
    marker: str
    linestyle: str | None = None


# --------------------------------------------------
#   Functions
# --------------------------------------------------

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


def plot_parameter_results(
        results: dict[str, dict[str, pd.DataFrame]],
        parameter: str,
        per_result_plot_data: dict[str, ResultPlotData],
        title: str,
        xlabel: str,
        ylabel: str,
        y_multiplier: float = 1,
) -> None:
    # Plot the total energy loss vs. DC link voltage for both devices
    plt.figure(figsize=(10, 6))
    color_cycle = itertools.cycle(plt.rcParams['axes.prop_cycle'].by_key()['color'])
    for device_key, per_parameter_results in results.items():
        parameter_results = per_parameter_results[parameter]
        color = next(color_cycle)
        for result_key, result_plot_data in per_result_plot_data.items():
            plt.plot(
                parameter_results[parameter],
                parameter_results[result_key] * y_multiplier,
                marker=result_plot_data.marker,
                label=f"{device_key} {result_plot_data.label}",
                color=color,
                linestyle=result_plot_data.linestyle,
            )

    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    plt.show()
