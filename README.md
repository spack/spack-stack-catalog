# Spack Stack Catalog

![assests/img/spack-stacks-blue.png](assests/img/spack-stacks-blue.png)

This is the spack stack community catalog, or spack.yaml files discovered
in the wild across the community! It is inspired by the [snakemake-workflow-catalog](https://github.com/snakemake/snakemake-workflow-catalog)
that is released under an [MIT LICENSE](.github/SNAKEMAKE-LICENSE).

⭐ [View the Catalog](https://spack.github.io/spack-stack-catalog/) ⭐

**this repository is still under development!**

## Usage

### Install Dependencies

The update of repositories that have spack.yaml is done during an automated CI,
however you might want to run the update script locally. You can first install
requirments:

```bash
python -m venv env
pip install -r requirements.txt
```

and spack should also be on your path.

```bash
which spack
```

### Environment

You'll need to export a personal access token as `GITHUB_TOKEN`:

```bash
export GITHUB_TOKEN=xxxxxxxxxxx
```

### Run update script

Then, run the script!

```bash
python scripts/generate-catalog.py
```

This should be run nightly to update the stacks here.

## License

Spack is distributed under the terms of both the MIT license and the
Apache License (Version 2.0). Users may choose either license, at their
option.

All new contributions must be made under both the MIT and Apache-2.0
licenses.

See [LICENSE-MIT](https://github.com/spack/spack/blob/develop/LICENSE-MIT),
[LICENSE-APACHE](https://github.com/spack/spack/blob/develop/LICENSE-APACHE),
[COPYRIGHT](https://github.com/spack/spack/blob/develop/COPYRIGHT), and
[NOTICE](https://github.com/spack/spack/blob/develop/NOTICE) for details.

SPDX-License-Identifier: (Apache-2.0 OR MIT)

LLNL-CODE-811652
