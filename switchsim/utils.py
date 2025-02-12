""" Utils

"""

# --------------------------------------------------
#   Imports
# --------------------------------------------------

import dataclasses
from pathlib import Path


# --------------------------------------------------
#   Exports
# --------------------------------------------------

__all__ = [
    "dataclass_to_dict",
    "verbose_print",
    "delete_files_with_same_name",
]


# --------------------------------------------------
#   Functions
# --------------------------------------------------

def dataclass_to_dict(dataclass) -> dict:
    # Convert dataclass fields to dictionary
    data = dataclasses.asdict(dataclass)

    # Add computed properties manually
    properties = {
        attr: getattr(dataclass, attr) for attr in dir(dataclass)
        if isinstance(getattr(type(dataclass), attr, None), property)
    }

    # Merge the dictionaries
    return {**data, **properties}


def verbose_print(is_verbose: bool, *args, **kwargs) -> None:
    if is_verbose:
        print(*args, **kwargs)


def delete_files_with_same_name(directory: Path, file_name: str) -> None:
    # Get the path without extension
    base_path = directory / file_name

    for file in directory.iterdir():
        if file.stem == base_path.stem or str(file.stem).split(".")[0] == base_path.stem:  # Compare filename without extension
            file.unlink()
