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

Create an environment with your favourite tool (venv, conda/mamba, uv, pixi, etc.)
and activate it.

Install with pip (alternatively, with `conda develop`):

```bash
python3 -m pip install -e .[dev]
```

### Guideline

- All code should have tests (or at least try, some are still missing).

- All code should have a minimal documentation
  (tolerance for private functions/method).

- Before submitting a merge request, please add test (if this is a new feature),
  and run all tests.


### Roadmap

The goal of martpy is to provide users a full API to create/manage MARTHE
models with python.

Some features are currently missing: some are identified as issues
in gitlab repo, created by users or the development team, some are marked as
TODOs in the source code (as the team grows, that's something we might not use
anymore :)), and, of course, some might not be identified yet.

To identify possible contributions, you can:

- check existing Issues (and please check is already assigned to a contributor),
- use the TODOs in the code: `grep -inr 'TODO' src/`


### Formatting code

#### Code format:

- Set up your editor to follow [PEP 8](https://www.python.org/dev/peps/pep-0008/),
  as closely as possible (remove trailing white space, no tabs, etc.). To help:

  + Check code with ruff, using the `./ruff.toml` file (also set your editor to use
    this project local file before a global configuration; e.g. for VSCode/VSCodium after
    installing ruff extension, add this in you `settings.json`:
    `"ruff.configurationPreference": "filesystemFirst"`).

  + use the `editorconfig` file (https://editorconfig.org/): nothing to do for
    vim, emacs, pycharm ; extension required for VSCode/VSCodium.

- Use the following import conventions:
  ```python
  import martpy as mart
  ```

#### Docstrings:

- numpy style, see [numpydoc](https://numpydoc.readthedocs.io/)


#### AI:

- responsability: it is developers' responsibility to only
  submit code they fully understand and are able to explain,
  for maintainability.
- merging code from AI assistant: All code need
  to be human reviewed and tested before any merge.
  In particular, AI generated code should never be merged in `dev` or
  `main` branches without human approval.
- attribution: please add `Assisted-by: AGENT_NAME MODEL_VERSION` at the
  end of your commit message (multiline) that add AI generated code,
  with AGENT_NAME and MODEL_VERSION being replaced with the relevant name
  (e.g. Devstral 2, Claude Sonnet 4.6, etc.).
  See (inspired from) https://docs.kernel.org/process/coding-assistants.html

Disclaimer: These few rules ares inspired by major open-source projects such as
NumPy or the Linux kernel.

Commits
-------

Write your commit messages preferably using standard prefixes for commit messages,
using [Conventional Commits specifications](https://www.conventionalcommits.org/):

| Commit prefix | Description |
| --------------|------------ |
|  **fix:**     |   fix for runtime crash or incorrect result *(correlated with patch in semver)*  |
|  **feat:** or **add:** | new functionality, correlated with *(correlated with minor in semver)* |
|  **change:**  | code change (e.g. change of default value, change of algorithm, etc.) |
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
  This also should lead to major semver change.
- Use the imperative mood in the subject line ("fix", not "fixed" or "fixes").
- optional scope can be added after the prefix, separated by a parenthesis.
  For example: `feat(cli): new cli entry point for XXXXX`.
- When fixing a bug, or working on a specific issue, the commit message should
  include the issue number. For example: subject line: `fix: bug #12` ; and/or end in
  the optional footer with `Closes #12` or `Fixes #12`.
  This will allow to automatically close the issue when merging the commit.
  See [closing issues via commit messages](https://docs.gitlab.com/ee/user/project/issues/managing_issues.html#closing-issues-automatically)
  for more details.
- Include co-authors in the footer if needed, using the `Co-authored-by: name <email>` syntax.

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


Branch
------

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
