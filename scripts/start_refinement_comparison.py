#!/usr/bin/env python3
"""Fetch a pinned checkout and run the accepted user head without replacing local edits."""
import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess
import tempfile
import uuid


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


CLASS_MATCH_POLICY = 'ignore_docstrings_and_argument_return_annotations_v1'


class _ComparisonSyntax(ast.NodeTransformer):
    """Normalize metadata only; the pinned class never inspects this metadata."""
    @staticmethod
    def without_docstring(node):
        if (node.body and isinstance(node.body[0], ast.Expr) and
                isinstance(node.body[0].value, ast.Constant) and
                isinstance(node.body[0].value.value, str)):
            node.body = node.body[1:]
        return node

    def visit_ClassDef(self, node):
        return self.without_docstring(self.generic_visit(node))

    def visit_FunctionDef(self, node):
        node.returns = None
        return self.without_docstring(self.generic_visit(node))

    def visit_arg(self, node):
        node.annotation = None
        return node


def comparison_class(value):
    nodes = [node for node in ast.parse(value).body
             if isinstance(node, ast.ClassDef) and node.name == 'LocalResidualHead']
    if len(nodes) != 1:
        raise ValueError('Expected exactly one submitted class LocalResidualHead')
    return _ComparisonSyntax().visit(nodes[0])


def class_syntax(value):
    return ast.dump(comparison_class(value), include_attributes=False)


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')


def run_existing_source(original, source, learner, *, helper=None):
    """Run a separate source checkout; mocks in tests never count as experiments."""
    original, source, learner = map(lambda p: Path(p).resolve(), (original, source, learner))
    submitted = learner.read_bytes()
    accepted = (source/'src/pathology_edge/learner_refinement.py').read_bytes()
    if class_syntax(submitted) != class_syntax(accepted):
        diff = ''.join(difflib.unified_diff(
            (ast.unparse(comparison_class(accepted))+'\n').splitlines(keepends=True),
            (ast.unparse(comparison_class(submitted))+'\n').splitlines(keepends=True),
            fromfile='reviewed class', tofile='local submitted class'))
        raise ValueError('The submitted class implementation differs after ignoring docstrings and '
                         'argument/return annotations. No training started and no local code was replaced. '
                         'Send the differences below for review:\n'+diff)
    if helper is None:
        helper = runpy.run_path(str(source/'scripts/run_model_comparison.py'))
    work = source/'work'
    work.mkdir(exist_ok=True)
    status_path = work/'launcher-status.json'
    if status_path.exists():
        raise FileExistsError('This source already has an attempt; keep its evidence and use a fresh checkout.')
    (work/'SOURCE_PATH.txt').write_text(str(source)+'\n')
    (work/'submitted_learner_refinement.py').write_bytes(submitted)
    before = dict(checkout=helper['original_state'](original),
                  learner_file=str(learner), learner_sha256=sha_bytes(submitted))
    dump(work/'original-before.json', before)
    dump(work/'learner-connection.json', dict(
        submitted_file_sha256=sha_bytes(submitted), accepted_file_sha256=sha_bytes(accepted),
        class_ast_sha256=sha_bytes(class_syntax(accepted).encode()),
        class_ast_matches=True, class_match_policy=CLASS_MATCH_POLICY,
        training_source='accepted class in the pinned source; local file is preserved'))
    status = dict(status='running', all_checks_passed=False, original_files_preserved=False)
    dump(status_path, status)
    print('SOURCE_DIR='+str(source), flush=True)
    output = work/('my-vit-refinement.'+uuid.uuid4().hex[:12])
    try:
        result = helper['run'](source, original/'data', output, comparison='refinement', seed=20261116)
        if (not isinstance(result, dict) or result.get('all_checks_passed') is not True or
                result.get('original_files_preserved') is not True):
            raise RuntimeError('Comparison did not report verified completion')
        status.update(status='completed', all_checks_passed=True, run=str(output))
    except BaseException as exc:
        status.update(status='failed', error=type(exc).__name__, message=str(exc))
        raise
    finally:
        after = dict(checkout=helper['original_state'](original), learner_file=str(learner),
                     learner_sha256=sha_bytes(learner.read_bytes()) if learner.is_file() else None)
        dump(work/'original-after.json', after)
        preserved = after == before
        status['original_files_preserved'] = preserved
        if not preserved:
            status.update(status='failed', all_checks_passed=False,
                          message='Original checkout or exercise file changed')
        dump(status_path, status)
        print('ORIGINAL_FILES_PRESERVED='+str(preserved).lower(), flush=True)
        if not preserved:
            raise RuntimeError('Original checkout or exercise file changed; inspect original-before/after.json')
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--source-commit', required=True)
    args = parser.parse_args()
    original = args.repo.resolve()
    if not re.fullmatch('[0-9a-f]{40}', args.source_commit):
        parser.error('Use the full pinned 40-character source commit')
    root = subprocess.check_output(['git', '-C', str(original), 'rev-parse', '--show-toplevel'], text=True).strip()
    if Path(root).resolve() != original:
        parser.error('--repo must be the repository root')
    learner = original/'work/step57-refinement/learner_refinement.py'
    for path in (learner, original/'data/manifest.json'):
        if not path.is_file():
            parser.error('Required file missing: '+str(path))
    work = original/'work'
    source = Path(tempfile.mkdtemp(prefix='refinement-source.', dir=work))
    print('PREPARING_SOURCE_DIR='+str(source), flush=True)
    subprocess.run(['git', '-C', str(original), 'fetch', 'origin', args.source_commit], check=True)
    subprocess.run(['git', '-C', str(original), 'worktree', 'add', '--detach', str(source), args.source_commit], check=True)
    actual = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != args.source_commit:
        raise ValueError('Source commit differs from the pinned commit')
    run_existing_source(original, source, learner)


if __name__ == '__main__':
    main()
