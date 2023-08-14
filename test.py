import os
import re
import sys
import tarfile
import unittest
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from shutil import copytree, rmtree
from subprocess import DEVNULL, check_call, check_output
from tempfile import TemporaryDirectory
from typing import Iterator, Tuple

import generate_dockerignore as lib


CASES_DIR = Path(__file__).parent / 'test_cases'
HIDDEN_PFX = '-'
COPYALL_DOCKERFILE = b'FROM scratch\nCOPY . .\n'


def tar_files(tar_bytes: bytes) -> Iterator[Tuple[Path, bytes]]:
  with tarfile.open(fileobj=BytesIO(tar_bytes)) as tar_file:
    for member in tar_file:
      if member.isfile():
        yield Path(member.path), tar_file.extractfile(member).read()


class Test(unittest.TestCase):

  @contextmanager
  def case_copy(self, case_orig: Path) -> Iterator[Tuple[Path, dict]]:
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

      yield case_copy, dict(cwd=repo_copy, env={**os.environ, 'HOME': home_copy})

  def expected_files(self, case_copy: Path) -> Iterator[Tuple[Path, bytes]]:
    base_path = case_copy / 'expected_repo_files'
    yield from (
      (path.relative_to(base_path), path.read_bytes())
      for path in base_path.glob('**/*')
      if path.is_file()
    )

  def actual_git_repo_files(self, repo_env: dict) -> Iterator[Tuple[Path, bytes]]:
    # add and commit so `git archive` produces a tar file that excludes ignored files
    check_call(['git', 'add', '.'], stdout=DEVNULL, **repo_env)
    check_call(['git', 'commit', '-m', 'Initial commit'], stdout=DEVNULL, **repo_env)
    yield from tar_files(check_output(['git', 'archive', 'HEAD'], **repo_env))

  def actual_docker_repo_files(self, repo_env: dict) -> Iterator[Tuple[Path, bytes]]:
    yield from tar_files(check_output(
      ['docker', 'build', '-q', '-f-', '-otype=tar,dest=-', '.'],
      input=COPYALL_DOCKERFILE,
      cwd=repo_env['cwd'],
    ))

  def write_actual_files(self, to_path: Path, files: Iterator[Tuple[Path, bytes]]):
    rmtree(to_path, ignore_errors=True)
    for rel_path, bytes in files:
      if rel_path.name.startswith('.'):
        rel_path = rel_path.with_name(re.sub('^.', HIDDEN_PFX, rel_path.name))

      dst_path = to_path / rel_path
      dst_path.parent.mkdir(parents=True, exist_ok=True)
      dst_path.write_bytes(bytes)

  def test(self):
    for case_orig in (child for child in CASES_DIR.iterdir() if child.is_dir()):
      with self.subTest(test_case=case_orig.name):
        with self.case_copy(case_orig) as (case_copy, repo_env):

          expected_output = (case_orig / 'expected_output').read_text()
          actual_output = check_output([sys.executable, lib.__file__], text=True, **repo_env)

          with self.subTest(attr='output'):
            (case_orig / 'actual_output').write_text(actual_output)
            self.assertMultiLineEqual(expected_output, actual_output)

          expected_files = dict(self.expected_files(case_copy))

          for method in (self.actual_docker_repo_files, self.actual_git_repo_files):
            with self.subTest(attr=method.__name__):
              actual_files = dict(method(repo_env))
              self.write_actual_files(case_orig / method.__name__, actual_files.items())
              self.assertDictEqual(expected_files, actual_files)


if __name__ == '__main__':
  unittest.main()
