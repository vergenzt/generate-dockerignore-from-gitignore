import os
import re
import sys
import tarfile
import unittest
from contextlib import contextmanager
from functools import partial
from io import BytesIO
from pathlib import Path
from shutil import copytree, rmtree
from subprocess import DEVNULL, check_call, check_output
from tempfile import TemporaryDirectory
from typing import Dict, Iterable, Iterator, Tuple, TypedDict

from parameterized import parameterized_class  # type: ignore

import generate_dockerignore as lib


CASES_DIR = Path(__file__).parent / 'cases'
HIDDEN_PFX = '-'


class RepoEnv(TypedDict):
  cwd: Path
  env: Dict[str, str]


def tar_files(tar_bytes: bytes) -> Iterator[Tuple[Path, str]]:
  with tarfile.open(fileobj=BytesIO(tar_bytes)) as tar_file:
    for member in tar_file:
      if member.isfile():
        yield Path(member.path), tar_file.extractfile(member).read().decode() # type: ignore


@parameterized_class(
  ['case_orig'],
  [[case] for case in filter(Path.is_dir, CASES_DIR.iterdir())],
  class_name_func=lambda cls, num, params: f'{cls.__name__}_{params["case_orig"].name}' # type: ignore
)
class TestCase(unittest.TestCase):
  case_orig: Path

  @contextmanager
  def case_copy(self, case_orig: Path) -> Iterator[Tuple[Path, RepoEnv]]:
    with TemporaryDirectory(dir=case_orig.parent, prefix=case_orig.name + '.copy.') as case_copy_str:
      case_copy = Path(case_copy_str)
      home_copy = case_copy / 'source_files' / 'home'
      repo_copy = home_copy / 'repo'

      copytree(case_orig, case_copy, dirs_exist_ok=True)

      # rename files starting with HIDDEN_PFX to start with `.` instead
      for git_file in case_copy.glob(f'**/{HIDDEN_PFX}*'):
        git_file.rename(git_file.with_name(re.sub(f'^{HIDDEN_PFX}', '.', git_file.name)))

      check_call(['git', 'init', repo_copy], stdout=DEVNULL)
      check_call(['git', 'config', 'user.name', 'Test User'], cwd=repo_copy, stdout=DEVNULL)
      check_call(['git', 'config', 'user.email', 'testuser@example.com'], cwd=repo_copy, stdout=DEVNULL)

      yield case_copy, RepoEnv(
        cwd=repo_copy,
        env={
          **os.environ,
          'HOME': str(home_copy),
          'XDG_CONFIG_HOME': str(home_copy / '.config'),
        }
      )

  def expected_files(self, case_copy: Path) -> Iterator[Tuple[Path, str]]:
    base_path = case_copy / 'expected_repo_files'
    yield from (
      (path.relative_to(base_path), path.read_text())
      for path in base_path.glob('**/*')
      if path.is_file()
    )

  def actual_git_repo_files(self, repo_env: RepoEnv) -> Iterator[Tuple[Path, str]]:
    # add and commit so `git archive` produces a tar file that excludes ignored files
    check_call(['git', 'add', '.'], stdout=DEVNULL, **repo_env)
    check_call(['git', 'commit', '-m', 'Initial commit'], stdout=DEVNULL, **repo_env)
    tar_bytes = check_output(['git', 'archive', 'HEAD'], **repo_env)
    yield from tar_files(tar_bytes)

  def actual_docker_repo_files(self, dockerfile: Path, repo_env: RepoEnv) -> Iterator[Tuple[Path, str]]:
    yield from tar_files(check_output(
      ['docker', 'build', '-q', '-f', dockerfile, '-otype=tar,dest=-', '.'],
      cwd=repo_env['cwd'],
    ))

  def write_actual_files(self, to_path: Path, files: Iterable[Tuple[Path, str]]):
    rmtree(to_path, ignore_errors=True)
    for rel_path, contents in files:
      if rel_path.name.startswith('.'):
        rel_path = rel_path.with_name(re.sub('^.', HIDDEN_PFX, rel_path.name))

      dst_path = to_path / rel_path
      dst_path.parent.mkdir(parents=True, exist_ok=True)
      dst_path.write_text(contents)

  def test(self):
    with self.case_copy(self.case_orig) as (case_copy, repo_env):

      expected_output = (self.case_orig / 'expected_output').read_text()
      actual_output = check_output([sys.executable, lib.__file__], text=True, **repo_env)

      with self.subTest(attr='output'):
        (self.case_orig / 'actual_output').write_text(actual_output)
        self.assertMultiLineEqual(expected_output, actual_output)

      expected_files = dict(self.expected_files(case_copy))

      actual_file_methods = [
        partial(self.actual_docker_repo_files, self.case_orig.parent / 'Dockerfile', repo_env),
        partial(self.actual_git_repo_files, repo_env),
      ]

      for method in actual_file_methods:
        with self.subTest(attr=method.func.__name__):
          actual_files = dict(method())

          # replace dynamic paths with placeholders during testing
          for path in actual_files:
            actual_files[path] = actual_files[path].replace(repo_env['env']['HOME'], '$HOME')

          self.write_actual_files(self.case_orig / method.func.__name__, actual_files.items())

          self.assertSetEqual(set(expected_files.keys()), set(actual_files.keys()))
          for path, expected_contents in expected_files.items():
            with self.subTest(path=path):
              self.assertMultiLineEqual(expected_contents, actual_files[path])


if __name__ == '__main__':
  unittest.main()
