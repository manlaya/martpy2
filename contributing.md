Contributing
============

Bug reports / Feature requests
------------------------------

If you have found a bug in martpy, or if you would like to suggest an improvement,
please submit a new Issue (or Work Item) in the Gitlab repo:

https://gitlab.com/brgm/hydrogeological-modelling/marthe-tools/martpy/-/issues

Please check if your Issue/suggestion is already existing before creating a new
one.


Code contribution
-----------------

### Getting started with martpy repo

Get the sources :

```bash
git clone https://gitlab.com/brgm/codes-hydrogeologiques/marthe-tools/martpy.git
```

Create an environment with your favourite tool (venv, conda/mamba, uv, pixi,
etc.) and activate it.

Install with pip (alternatively, with `conda develop`):

```bash
python3 -m pip install --group=dev -e .
```

### Guideline

- All code should have tests (or at least try, some are still missing).

- All code should have a minimal documentation
  (tolerance for private functions/method).

- Follow the [Code style](#code-style) section below.

- Install git pre-commit hooks:

```bash
pip install pre-commit
pre-commit install --install-hooks
```

- Before submitting a merge request:
  + make sure your local branch is up to date with `dev`:
    `git pull --rebase origin dev` (resolve conflicts if any, keep dev branch
    content, or combination unless your patch solve this specific conflict)
  + add test(s) for your patch, and run `pytest` in the root directory to check
    your code with pytest (make sure all tests pass).


### Roadmap

The goal of `martpy` is to provide users a full API to create/manage MARTHE
models with python.

Some features are currently missing: some are identified as issues
in gitlab repo, created by users or the development team, some are marked as
TODOs in the source code (as the team grows, that's something we might not use
anymore :)), and, of course, some might not be identified yet.

To identify possible contributions, you can:

- check existing Issues (and please check is already assigned to a contributor),
- raise new issue if you find a bug or want to propose a new feature,
- use the TODOs in the code: `grep -inr 'TODO' src/`


### Code style

#### Linters and formatters

We mostly (try to) follow the standard Python style conventions as described
here:

- Python code style [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Python docstring basics [PEP 257](https://peps.python.org/pep-0257/)
- Docstring convention from numpy [numpydoc](https://numpydoc.readthedocs.io/)

Additional rules may be found in the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
(! except for docstrings: please follow numpy rules from numpydoc).


To help you with that, a few config files are provided:

- **lint** : Check code with ruff (linting), using the `./ruff.toml` file
  (also set your editor to use this project local file before a global
  configuration; e.g.  for VSCode/VSCodium after installing ruff extension,
  add this in your `settings.json`:
  `"ruff.configurationPreference": "filesystemFirst"`).

  This will warn you about import sorting (isort), flake8 and pep8 rules, etc.
  within your editor.

  `martpy` does not strictly follow Black formatting rules, only a few
  common rules are enforced with ruff. See `./ruff.toml` for more, and `yapf`
  bullet point below for formatting.

- **editorconfig** use the `.editorconfig` file (https://editorconfig.org/):
  nothing to do for vim, emacs, pycharm; extension required for VSCode/VSCodium.
  This is used to harmonize indentation, line endings, etc.

- (optional) **format** : Additionally, a `.style.yapf` is provided to help
  you format your code, with a configurable tool ([yapf](https://github.com/google/yapf)).
  Run `yapf --diff your/modified/file.py` to see the difference, apply what
  you want. Using vim or vscodium, you can configure keybindings to format
  selection only (for vim, use the plugin provided in yapf repo).

  Please do not use `black` (or `ruff format`) on all project. Format only
  your code.


Additionally, use the following import conventions:

```python
import martpy as mart
```

#### Docstrings

Follow the numpydoc format for docstrings. See
[numpydoc](https://numpydoc.readthedocs.io/en/latest/format.html)

For validity checks, see https://numpydoc.readthedocs.io/en/latest/validation.html


Commits
-------

Write your commit messages preferably using standard prefixes for commit messages,
using [Conventional Commits specifications](https://www.conventionalcommits.org/):

| Commit prefix | Description |
| --------------|------------ |
|  **fix:**     |   fix for runtime crash or incorrect result *(correlated with patch in semver)*  |
|  **feat:** or **add:** | new functionality, correlated with *(correlated with minor in semver)* |
|  **change:**  | code change (e.g. change of default value, change of algorithm, etc.) *(possibly correlated with major in semver)*  |
| **refactor:** | code refactoring |
|  **style:**   | coding style / Non-functional format/style changes only |
|  **test:**    | New tests, corrections to existing tests, test refactors |
|  **doc:**     | documentation change |
|  **perf:**    | Performance improvements |
|  **build:**   | build system change |
|  **ci:**      | continuous integration pipelines / GitlabCI related changes |
|  **dev:** or **wip:** |  work in progress (not ready for merge) |
|  **revert:**  | Revert a previous commit — the commit message should identify the hash of the commit being reverted |
|  **chore:**   | miscellaneous changes that don't fit into the other categories (e.g. bump version) |


Commit message template:
```
<type>(optional scope)[!]: <subject>

[Optional body]

[Optional footer(s)]
```

Additional guidelines:
- **Breaking** changes can use an exclamation mark:
  `change!: optim values are now stored in XXXX`.
  This also should lead to *major semver change*.
- Use the imperative mood in the subject line ("fix", not "fixed" or "fixes").
- optional scope can be added after the prefix, separated by a parenthesis.
  For example: `feat(cli): new cli entry point for XXXXX`.
- When fixing a bug, or working on a specific issue, the commit message should
  include the issue number. For example: subject line: `fix: bug #12` ; and/or
  end in the optional footer with `Closes #12` or `Fixes #12`.
  This will allow to automatically close the issue when merging the commit.
  See [closing issues via commit messages](https://docs.gitlab.com/ee/user/project/issues/managing_issues.html#closing-issues-automatically)
  for more details.
- Include co-authors in the footer if needed, using the
  `Co-authored-by: name <email>` syntax.

All these rules will be used to feed the changelog, following
[keepachangelog.com](https://keepachangelog.com/en/1.1.0/)
and possibly using [git-cliff](https://git-cliff.org).


Example of full commit message:
```
fix: parsing value in XXX #12

Message details
Line 2

Co-authored-by: Toto <toto@toto.com>
Closes #12
```


Branches
--------

Branches should be named using the following convention:
`<type>/<short-description>`

The `<type>` should be one of the following:
-   `feat`: A new feature
-   `fix`: A bug fix

For example:
`feat/new-cli-entry-point` or `fix/bug-xxxx`.

The core development team can/may also use a branch for each developer:
`dev/<developer-name>`.

For example:
`dev/manlaya` or `dev/am` (or `dev-am`).


AI assistance
-------------

From numpydoc: "'AI' herein refers to generative AI tools like large language
models (LLMs) that can generate, edit, and review software code, create and
manipulate images, or generate human-like communication."

We have the following policy regarding AI:

- AI assistance is allowed, but the developer is responsible for the correctness
  of the code, its maintainability and its integration in the project. It is
  **developers' responsibility** to only submit code they fully understand and
  are able to explain, for maintainability.

- Merge requests: Merging code from AI assistant without human review is not
  allowed. All code need to be human reviewed and tested before any merge. In
  particular, AI generated code should never be merged in `dev` or `main`
  branches without human approval (never fully automated, e.g. no AI-only
  merges).

- Issues/Merge requests message: do not submit issues or merge requests fully
  written by AI assistant or agent. You can make a draft of the issue/MR with
  such tools, but then please edit yourself and rewrite it in your own words,
  avoid LLMs verbosity.
  See also https://numpy.org/devdocs/dev/ai_policy.html#communication for
  comments.  In MR, AI may be used for code/patches review, but the final
  decision should be human.

- Attribution: please add `Assisted-by: AGENT_NAME MODEL_VERSION` at the
  end of your commit message (multi-line) that add AI generated code,
  with AGENT_NAME and MODEL_VERSION being replaced with the relevant name
  (e.g. Devstral 2, Claude Opus 4.8, Gemma 4 31B, etc.).
  See (inspired from) https://docs.kernel.org/process/coding-assistants.html


*Disclaimer*: These few rules ares inspired by (taken from) the policies of major
open-source projects such as NumPy (https://numpy.org/devdocs/dev/ai_policy.html)
or the Linux kernel (https://docs.kernel.org/process/coding-assistants.html).
