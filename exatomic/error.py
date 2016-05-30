# -*- coding: utf-8 -*-
'''
Errors, Warnings, and Exceptions for atomic
============================================
'''
from exa.error import ExaException


class AtomicException(ExaException):
    pass


class StringFormulaError(AtomicException):
    '''
    The string representation of a :class:`~atomic.formula.SimpleFormula` has syntax described in
    :class:`~atomic.formula.SimpleFormula`.
    '''
    _msg = 'Incorrect formula {}. See SimpleFormula documentation and examples; H(2)O(1), H(1)Na(1)O(1), etc.'

    def __init__(self, formula):
        msg = self._msg.format(formula)
        super().__init__(msg)


class ClassificationError(AtomicException):
    '''
    Raised when a classifier for :func:`~atomic.molecule.Molecule.add_classification` used
    incorrectly.
    '''
    _msg = 'Classifier must be a tuple of the form ("identifier", "label", exact).'