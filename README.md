# pycallflow

[![PyPI - Version](https://img.shields.io/pypi/v/pycallflow.svg)](https://pypi.org/project/pycallflow)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pycallflow.svg)](https://pypi.org/project/pycallflow)

-----
## WARNING
Do not use pycallflow to map hostile or potentially malicious python code.  Code may be executed as it is examined.


**Table of Contents**

- [Installation](#installation)
- [License](#license)

## What is Pycallflow

Pycallflow produces GraphViz-compatible output that visually shows the flow of calls within a module, package, or directory of python files like this:
![Sample pycallflow graphic](images/pycallflow-full.png "Pycallflow of pycallflow")

I wrote it to help me get a grip on python projects that have accreted files and capability over time.  It was difficult to hand trace the call flows when their were problems and upgrades to be done.

There are limitations and some significant limitations.  Please see BLAH below

## What it does

Pycallflow recursively imports and analyzes the files in a module or directory to identify all of the declared entities (functions, methods, and classes).  It  maps the calls between these entities to produce a network graph which is then rendered in DOT language.

## Installation

```console
pip install pycallflow
```

## Usage

### Basics

Invoke with
```console
python -m pycallflow [target]
```
To generate a DOT-language call flow diagram of every discovered entity.

If you have GraphViz installed you can pipe it:
```console
python -m pycallflow [target] | dot -Tpng -ofilename.png
```
### Clean up

The diagrams can get quite busy, but there are three options that can limit some of the noise

#### suppress_recursive_calls

Entities that recurse on themselves will get loop indicators like this:

PIC HERE

```console
python -m pycallflow --suppress_recursive_calls [target]
```
Will result in the elimination of these loops:

PIC HERE

#### combine_calls

Entities may call the same entity more than once.  By default, this will show as multiple indicators:

PIC HERE

```console
python -m pycallflow --combine_calls [target]
```
Will allow on one indicator between entities:

PIC HERE

#### suppress_class_references

By default an entity that references a class will get an indicator similar to :

PIC HERE

This can be handy if an entity assigns a class reference to a variable.  However, it may be obvious that the entity is calling a class method in which case the "reference" indicator will just be added noise.

```console
python -m pycallflow --suppress_class_references [target]
```

Will clean these up:
PIC HERE





## License

`pycallflow` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
