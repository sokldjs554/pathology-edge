"""The Codespaces handoff must preserve the submitted file, even on failure."""
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

ROOT = Path(__file__).parents[1]


@pytest.fixture
def launcher():
    path = ROOT/'scripts/start_refinement_comparison.py'
    spec = importlib.util.spec_from_file_location('refinement_handoff', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def inputs(tmp_path):
    original, source = tmp_path/'original', tmp_path/'source'
    learner = original/'work/step57-refinement/learner_refinement.py'
    accepted = source/'src/pathology_edge/learner_refinement.py'
    learner.parent.mkdir(parents=True)
    accepted.parent.mkdir(parents=True)
    shutil.copy2(ROOT/'src/pathology_edge/learner_refinement.py', learner)
    shutil.copy2(learner, accepted)
    return original, source, learner


def helper(calls, action=None):
    def run(*args, **kwargs):
        calls.append((args, kwargs))
        if action:
            action()
        return {'all_checks_passed': True, 'original_files_preserved': True}
    return {'original_state': lambda repo: {'commit': 'fixture', 'status': ' M learner_wsi.py'},
            'run': run}


def test_matching_submission_trains_fixed_pair_and_preserves_source(launcher, inputs):
    original, source, learner = inputs
    # Formatting/comments may differ; the submitted class syntax must match.
    learner.write_text('# My local copy\n'+learner.read_text())
    before = learner.read_bytes()
    calls = []
    report = launcher.run_existing_source(original, source, learner, helper=helper(calls))
    assert report['all_checks_passed'] and report['original_files_preserved']
    assert learner.read_bytes() == before
    assert calls[0][0][:2] == (source, original/'data')
    assert calls[0][1] == {'comparison': 'refinement', 'seed': 20261116}
    assert (source/'work/submitted_learner_refinement.py').read_bytes() == before


@pytest.mark.parametrize('change', ['scaffold_docstring', 'method_docstring',
                                  'return_annotation', 'remove_annotations'])
def test_documentation_and_type_hints_do_not_reject_reviewed_computation(launcher, inputs, change):
    original, source, learner = inputs
    text = learner.read_text()
    if change == 'scaffold_docstring':
        text = text.replace('Raw logits -> same-shaped raw logits.',
                            'Raw logits -> same-shaped raw logits; requirements in docs/STEP_57.md.')
    elif change == 'method_docstring':
        text = text.replace('        super().__init__()',
                            '        """Initialize the two local layers."""\n        super().__init__()')
    elif change == 'return_annotation':
        text = text.replace('def __init__(self):', 'def __init__(self) -> None:')
    else:
        text = text.replace('logits: torch.Tensor', 'logits').replace(') -> torch.Tensor:', '):')
    learner.write_text(text)
    before = learner.read_bytes()
    calls = []
    report = launcher.run_existing_source(original, source, learner, helper=helper(calls))
    assert report['all_checks_passed'] and len(calls) == 1
    assert learner.read_bytes() == before
    connection = json.loads((source/'work/learner-connection.json').read_text())
    assert connection['class_ast_matches'] is True
    assert connection['class_match_policy'] == 'ignore_docstrings_and_argument_return_annotations_v1'
    assert connection['submitted_file_sha256'] != connection['accepted_file_sha256']


def test_different_submission_stops_before_training(launcher, inputs):
    original, source, learner = inputs
    learner.write_text(learner.read_text().replace('return logits + correction', 'return logits - correction'))
    calls = []
    with pytest.raises(ValueError, match='submitted class') as error:
        launcher.run_existing_source(original, source, learner, helper=helper(calls))
    assert calls == []
    assert '-        return logits + correction' in str(error.value)
    assert '+        return logits - correction' in str(error.value)


@pytest.mark.parametrize('old,new', [('padding=1', 'padding=0'),
                                   ('nn.init.zeros_(self.conv2.weight)', 'nn.init.ones_(self.conv2.weight)'),
                                   ('        _validate_logits(logits)\n', ''),
                                   ('torch.relu', 'torch.sigmoid')])
def test_operation_and_layer_changes_still_stop_before_training(launcher, inputs, old, new):
    original, source, learner = inputs
    learner.write_text(learner.read_text().replace(old, new))
    calls = []
    with pytest.raises(ValueError):
        launcher.run_existing_source(original, source, learner, helper=helper(calls))
    assert calls == []


def test_training_failure_preserves_evidence_without_success(launcher, inputs):
    original, source, learner = inputs
    def fail():
        raise RuntimeError('synthetic training failure')
    with pytest.raises(RuntimeError, match='synthetic training failure'):
        launcher.run_existing_source(original, source, learner, helper=helper([], fail))
    report = json.loads((source/'work/launcher-status.json').read_text())
    assert report['status'] == 'failed' and report['all_checks_passed'] is False
    assert report['original_files_preserved'] is True


def test_ignored_exercise_file_mutation_cannot_be_reported_as_success(launcher, inputs):
    original, source, learner = inputs
    def change():
        learner.write_text('# unexpectedly changed')
    with pytest.raises(RuntimeError, match='Original checkout or exercise file changed'):
        launcher.run_existing_source(original, source, learner, helper=helper([], change))
    report = json.loads((source/'work/launcher-status.json').read_text())
    assert report['status'] == 'failed' and report['original_files_preserved'] is False


@pytest.mark.parametrize('field', ['all_checks_passed', 'original_files_preserved'])
def test_unverified_return_value_cannot_become_success(launcher, inputs, field):
    original, source, learner = inputs
    functions = helper([])
    result = {'all_checks_passed': True, 'original_files_preserved': True}
    result[field] = False
    functions['run'] = lambda *args, **kwargs: result
    with pytest.raises(RuntimeError, match='verified completion'):
        launcher.run_existing_source(original, source, learner, helper=functions)
    report = json.loads((source/'work/launcher-status.json').read_text())
    assert report['status'] == 'failed' and report['all_checks_passed'] is False
