## Local dev setup

Install dependencies:
```console
virtualenv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
pre-commit install
```

Then, make your code changes, and run `pre-commit` (or just attempt to commit) and your code will be
linted and tests will be run.
