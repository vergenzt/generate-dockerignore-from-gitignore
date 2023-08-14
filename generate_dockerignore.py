#!/usr/bin/env python3
'''
.dockerignore file generator based on .gitignore file(s)

Handles the following differences:

| behavior                                    | .gitignore            | .dockerignore             |
| ------------------------------------------- | --------------------- | ------------------------- |
| plain patterns without slashes or wildcards | ⏬️ match recursively  | ⬆️ match top-level only   |
| separate per-directory ignore files         | ✅ allowed            | ❌ not allowed            |
| local .git/info/exclude file                | ✅ included           | -                         |
| global core.excludesFile file               | ✅ included           | -                         |


References:
- https://git-scm.com/docs/gitignore
- https://docs.docker.com/engine/reference/builder/#dockerignore-file
'''

import argparse
import logging
import os
import re
from pathlib import Path
from subprocess import run
import sys
from typing import IO, Iterator, Optional, cast


__version__ = 0.1


def gitignore_pat_from_line(line: str) -> Optional[str]:
  if not line.startswith('#') and (stripped := line.strip()):
    return stripped


def gitignore_pat_to_dockerignore_pat(from_gitignore: Path, line: str) -> str:
  if pat := gitignore_pat_from_line(line):
    [(negator, file_pat)] = re.findall('^(!?)(.*)', pat)
    relativizer = str(from_gitignore.parent) + '/' if from_gitignore.name == '.gitignore' else ''
    recursivizer = '**/' if '/' not in file_pat.rstrip('/') else ''
    return ''.join([
      negator,
      relativizer,
      recursivizer,
      file_pat,
    ])
  else:
    return line


def generate_dockerignore_lines(gitignore: Path) -> Iterator[str]:
  logging.debug(f'Processing {gitignore}')
  yield f'### from: {gitignore}'
  yield from ((
    gitignore_pat_to_dockerignore_pat(gitignore, line)
    for line in gitignore.read_text().splitlines()
  ))
  yield ''
  yield ''


def find_gitignore_files(root: Path) -> Iterator[Path]:
  if root.is_file():
    yield root
  else:
    # https://git-scm.com/docs/gitignore

    yield from root.glob('**/.gitignore')

    if git_dir := run(['git', '-C', root, 'rev-parse', '--git-dir'], text=True, capture_output=True).stdout.strip():
      yield from Path(git_dir).glob('info/exclude')

    if config_val := run(['git', 'config', '--get', 'core.excludesFile'], text=True, capture_output=True).stdout.strip():
      yield Path(config_val)
    elif config_home := os.getenv('XDG_CONFIG_HOME'):
      yield Path(config_home) / 'git' / 'ignore'
    elif home := os.getenv('HOME'):
      yield Path(home) / '.config' / 'git' / 'ignore'


def parse_args():
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('-C', '--docker-root', type=os.chdir, help='Docker context directory to chdir into before continuing')
  parser.add_argument('-v', '--verbose', dest='log_level', action='store_const', const=logging.DEBUG, default=logging.INFO, help=(
    'Output per-file logging to stderr'
  ))
  parser.add_argument('-o', '--output', type=argparse.FileType('w'), default='.dockerignore', help=(
    'File path for generated .dockerignore rule output, or - for stdout (default: %(default)s)'
  ))
  parser.add_argument('PATH', type=Path, nargs=argparse.ZERO_OR_MORE, default=[Path('.')], help=(
    'gitignore file(s), or directories under git source control (which will be searched\n'
    'for **/.gitignore).'
  ))
  return parser.parse_args()


def main():
  args = parse_args()
  logging.basicConfig(format='%(message)s', level=args.log_level, stream=sys.stdout)

  n_lines = 0
  prev_pats = []

  with cast(IO, args.output) as output:
    for path in args.PATH:
      output.writelines(line + '\n' for line in [
        f'### Generated by Python package {Path(__file__).parent.name}',
        '',
        '# excluding .git by default',
        '.git',
        '',
      ])

      for gitignore in filter(Path.exists, find_gitignore_files(path)):

        is_ignored = any(parent.match(pat) for pat in prev_pats for parent in gitignore.parents if not pat.startswith('!'))
        if is_ignored:
          logging.debug(f'Skipping {gitignore} due to parent path being ignored')

        else:
          file_lines = list(generate_dockerignore_lines(gitignore))
          file_pats = [pat for line in file_lines if (pat := gitignore_pat_from_line(line))]

          if file_pats:
            output.writelines(line + '\n' for line in file_lines)
            n_lines += len(file_lines)
            prev_pats.extend(file_pats)
          else:
            logging.debug(f'Skipping {gitignore} due to no patterns')

  logging.info(f'Wrote {n_lines} lines ({len(prev_pats)} patterns) to {output.name}')


if __name__ == '__main__':
  main()
