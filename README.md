# generate-dockerignore-from-gitignore

As the name implies, this package generates a `.dockerignore` for you based on `.gitignore` rules
found in your source tree.

Why generate this file, you ask? Because there are a number of differences between
`.dockerignore` and `.gitignore` rule processing which can make it non-trivial to make
your Docker file tree match your local git tree.

Generating your `.dockerignore` file based on your configured `.gitignore` rules means you only have
to think about which files should not be distributed with your project only once. This also can
promote reproducible builds by ensuring that the only files your Docker context has access to are
those files that are tracked by your git repository.

The following differences between `.dockerignore` vs `.gitignore` processing are handled by this tool:

| behavior                                    | .gitignore            | .dockerignore             |
| ------------------------------------------- | --------------------- | ------------------------- |
| plain patterns without slashes or wildcards | ⏬️ match recursively  | ⬆️ match top-level only   |
| separate per-directory ignore files         | ✅ allowed            | ❌ not allowed            |
| local .git/info/exclude file                | ✅ included           | -                         |
| global core.excludesFile file               | ✅ included           | -                         |

The code's handling of these behavioral differences is [tested](test/cases) using actual
git and Docker calls, followed by validation that the resultant git source trees are
equal to the Docker build contexts.

References:
- https://git-scm.com/docs/gitignore
- https://docs.docker.com/engine/reference/builder/#dockerignore-file

## Installation

```
pip install generate-dockerignore-from-gitignore
```

## Usage

<!--[[[cog
  os.environ['COLUMNS'] = '100'
  print('```')
  print(sp.check_output(['generate-dockerignore', '--help'], text=True, stderr=sp.STDOUT))
  print('```')
]]]-->
```
usage: generate-dockerignore [-h] [-C DOCKER_ROOT] [-v] [-o OUTPUT] [PATH ...]

.dockerignore file generator based on .gitignore file(s)

positional arguments:
  PATH                  gitignore file(s), or directories under git source control (which will be
                        searched for **/.gitignore).

options:
  -h, --help            show this help message and exit
  -C DOCKER_ROOT, --docker-root DOCKER_ROOT
                        Docker context directory to chdir into before continuing
  -v, --verbose         Output per-file logging to stderr
  -o OUTPUT, --output OUTPUT
                        File path for generated .dockerignore rule output, or - for stdout
                        (default: .dockerignore)

```
<!--[[[end]]] (checksum: 66f0bbbfd94d6d5536e726e18f537585)-->
