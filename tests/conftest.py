import pytest


def pytest_addoption(parser):
    parser.addoption("--run-learner", action="store_true", help="Run unfinished user exercises")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-learner"):
        for item in items:
            if item.get_closest_marker("learner") is not None:
                item.add_marker(pytest.mark.skip(reason="User exercise pending; use --run-learner"))

