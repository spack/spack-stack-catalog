#!/usr/bin/env python3

# **IMportant!** This is a development script to quickly get lists and then
# a matrix of packages. It is far from perfect, and I suspect buggy because
# the spack.yaml files come in so many different flavors. If you have an idea
# for how to clean this up, please submit a PR! It will be greatly appreciated!

from sklearn import manifold
import pandas
import logging
import fnmatch
import numpy
import os
import yaml

from jinja2 import Environment, FileSystemLoader, select_autoescape

logging.basicConfig(level=logging.INFO)

# We want the root
here = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

env = Environment(
    autoescape=select_autoescape(["html"]), loader=FileSystemLoader("templates")
)


def read_yaml(filename):
    with open(filename, "r") as fd:
        content = yaml.load(fd, Loader=yaml.FullLoader)
    return content


def recursive_find(base, pattern="*.yaml"):
    """recursive find will yield python files in all directory levels
    below a base path.

    Arguments:
      - base (str) : the base directory to search
      - pattern: a pattern to match, defaults to *.py
    """
    for root, _, filenames in os.walk(base):
        for filename in fnmatch.filter(filenames, pattern):
            yield os.path.join(root, filename)


def get_packages(key, content):
    """
    Return a list of packages found in a spack.yaml
    """
    found = set()
    if key not in content.get("spack", {}):
        return []
    specs = content.get("spack", {}).get(key, {})

    def get_definition(name):
        defs = content.get("spack", {}).get("definitions")
        specs = []
        if not defs:
            return []
        for definition in defs:
            if name in definition:
                specs = definition[name]
        return specs

    if not specs:
        specs = get_definition(key)

    if isinstance(specs, dict):
        specs = list(specs.keys())

    while specs:
        spec = specs.pop(0)

        # if it's a matrix
        if isinstance(spec, dict) and "matrix" in spec:
            for key in spec["matrix"][0]:
                specs += get_definition(key.strip("$"))
            continue

        # This is a reference to another variable
        if spec.startswith("$"):
            group = get_definition(spec.strip("$"))
            while group:
                spec = group.pop(0)
                if isinstance(spec, dict) and "matrix" in spec:
                    for key in spec["matrix"][0]:
                        group += get_definition(key.strip("$"))
                else:
                    for char in ["@", " ", "%", "~", "+"]:
                        spec = spec.split(char)[0]
                    found.add(spec.strip())
        else:
            for char in ["@", " ", "%", "~", "+"]:
                spec = spec.split(char)[0]
            found.add(spec.strip())

    if "all" in found:
        found.remove("all")
    return list(found)


def main():
    """
    Entrypoint to generation of graph data
    """
    # Keep track of envs and spack keys
    spack_keys = 0
    env_keys = 0

    # Get list of all spack.yaml files
    stacks = os.path.join(here, "_stacks")
    spackyamls = list(recursive_find(stacks))

    # First count the keys, and get unique package names
    packages = set()
    for spackyaml in spackyamls:
        # Try to get specs by parsing spack.yaml
        content = read_yaml(spackyaml)
        if not isinstance(content, dict):
            continue
        if "spack" in content:
            spack_keys += 1
        elif "env" in content:
            env_keys += 1

        # Try parsing both specs and packages. This is imperfect, but best effort
        [packages.add(x) for x in get_packages("specs", content)]
        [packages.add(x) for x in get_packages("packages", content)]

    # Create a data frame
    print("Found %s spack.yaml env keys and %s spack keys." % (env_keys, spack_keys))
    packages = sorted(list(packages))
    df = pandas.DataFrame(columns=packages, index=packages)
    df.fillna(0, inplace=True)

    # Now populate the data frame with counts
    print("Found %s spack.yaml env keys and %s spack keys." % (env_keys, spack_keys))
    for i, spackyaml in enumerate(spackyamls):
        print("Counting spack.yaml %s of %s" % (i, len(spackyamls)))
        # Try to get specs by parsing spack.yaml
        content = read_yaml(spackyaml)
        if isinstance(content, list):
            continue

        # Try parsing both specs and packages. This is imperfect, but best effort
        packageset = get_packages("specs", content) + get_packages("packages", content)
        for pkg1 in packageset:
            for pkg2 in packageset:
                df.loc[pkg1, pkg2] += 1

    # Save the counts (intermediate data)
    counts_df = os.path.join(here, "data", "package-pair-counts.csv")
    df.to_csv(counts_df)

    # We need to normalize by packages that appear across a lot of packages. So we want to divide by the square root of the row sums and the columns sums. We do this so it's still symmetric, and we use a square root because we want the units to go away.
    rowsums = numpy.sqrt(df.sum(axis=0))  # row and column sums are the same
    distinct = (df != 0).sum()

    # This is a symmetric matrix, min 0 and max 1.0 normalized counts
    normalized = df.divide(rowsums).transpose().divide(rowsums)
    counts_df = os.path.join(here, "data", "package-normalized-counts.csv")
    normalized.to_csv(counts_df)

    # If counts is high, distance is close. If counts is low, distance is far
    # 1 == packages only appear together, 0 == never appear together
    # now smaller is closer in distance
    distance = 1 / normalized  # this has inf
    distance.replace([numpy.inf, -numpy.inf], 0, inplace=True)
    counts_df = os.path.join(here, "data", "package-distances.csv")
    distance.to_csv(counts_df)

    # Make the tsne!
    fit = manifold.TSNE(n_components=2)
    embedding = fit.fit_transform(distance)
    df = pandas.DataFrame(embedding, index=distance.index, columns=["x", "y"])
    df.index.name = "name"

    # use normalization values for the radius (color)
    df["norm"] = rowsums
    df["distinct"] = distinct
    counts_df = os.path.join(here, "_data", "packages-embeddings.csv")
    df.to_csv(counts_df)


if __name__ == "__main__":
    main()
