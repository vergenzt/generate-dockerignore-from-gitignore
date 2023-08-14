usage: generate_dockerignore.py [-h] [-C DOCKER_ROOT] [-v] [-o OUTPUT]
                                [PATH ...]

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

positional arguments:
  PATH                  gitignore file(s), or directories under git source
                        control (which will be searched for **/.gitignore).

options:
  -h, --help            show this help message and exit
  -C DOCKER_ROOT, --docker-root DOCKER_ROOT
                        Docker context directory to chdir into before
                        continuing
  -v, --verbose         Output per-file logging to stderr
  -o OUTPUT, --output OUTPUT
                        File path for generated .dockerignore rule output, or
                        - for stdout (default: .dockerignore)
