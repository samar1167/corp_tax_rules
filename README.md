# Corporate Tax Rules Platform

This repository contains the first implementation of a rules-first tax
compliance platform focused on Indian ITR and corporate tax workflows.

## Stack

- Django
- SQLite for the initial persistence layer
- Django REST Framework for internal APIs

## Architecture

The implementation follows the rules-first approach captured in:

- `itr_approach.md`
- `ITR_Rule_System.md`
- `corporate_tax_approach.md`

Key principles:

- Rules are the source of truth.
- Primitives are complete, share-nothing rule units.
- Modules are assembled from primitives, decision tables, and computations.
- Governance owns cross-module rules.
- Approved versions are immutable and only superseded by new versions.

## Initial Apps

- `core_rules`: core rule/versioning models and setup pipeline
- `itr`: individual tax module
- `corporate_tax`: corporate tax module
- `governance`: cross-module rules and unified posture
- `audit`: immutable evaluation logging

## Local Setup

Once Python packaging tools are installed:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
