
import sys
import importlib
from pathlib import Path
import activitysim.abm  # register components # noqa: F401

# TODO: should this just be its own installable package?
ext_dir = str(Path(__file__).parents[1])
sys.path.insert(0, ext_dir)
extensions = importlib.import_module("extensions")  # register cvm components
sys.path = sys.path[1:]

EXPECTED_MODELS = [
    "cvm_accessibility",
    "route_generation",
    "route_purpose_and_vehicle",
    # "route_terminal",
    # "route_start_time",
    # "route_stop_generation",
]


def test_cvm():

    state = extensions.cvm_state.State.make_default(__file__, configs_dir=("configs", "../configs"))
    assert state.settings.models == EXPECTED_MODELS
    assert state.settings.chunk_size == 0
    assert not state.settings.sharrow

    # for step_name in EXPECTED_MODELS:
    #     state.run.by_name(step_name)
    #     print(f"> cvm_step {step_name}: ok")

    print()

    print("### commercial_accessibility ###")
    state.run.cvm_accessibility()
    print(state.dataset.commercial_accessibility)

    print("### route gen ###")
    state.run.route_generation()
    print(state.dataset.establishments)
    print(state.get("routes"))
    print(state.get("routes").info())

    print("### route purp and veh ###")
    state.run.route_purpose_and_vehicle()
