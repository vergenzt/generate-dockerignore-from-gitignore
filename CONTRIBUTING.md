## Local dev setup

Install dependencies:
```console
virtualenv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
pre-commit install
```

Then, make your code changes, and run `pre-commit` (or just attempt to commit) and your code will be
linted and tests will be run.

## Publishing

Set `.envrc` to the following contents:

```
export FLIT_USERNAME=__token__
export FLIT_PASSWORD=op://<op_vault_id>/<op_item_id>/FLIT_PYPI_API_TOKEN
```

Approve it with `direnv allow`, then, after bumping the `__version__` constant in the main source module, use `op run flit publish` to publish a new version to PyPI.
