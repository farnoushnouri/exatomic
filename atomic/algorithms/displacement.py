# -*- coding: utf-8 -*-
'''
Computation of Displacement
=============================
'''
import numpy as np
import pandas as pd


def absolute_squared_displacement(universe, ref_frame=None):
    '''
    Compute the mean squared displacement per atom per time with respect to the
    referenced position.

    Computes the squared displacement using the :class:`~atomic.atom.Atom`
    dataframe. In the case where this dataframe only contains the in unit cell
    coordinates, this may not give desired results.

    Args:
        universe (:class:`~atomic.Universe`): The universe containing atomic positions
        ref_frame (int): Which frame to use as the reference (default first frame)

    Returns
        df (:class:`~pandas.DataFrame`): Time dependent displacement per atom
    '''
    index = 0
    if ref_frame is None:
        ref_frame = universe.frame.index[index]
    else:
        frames = universe.frame.index.values
        ref_frame = np.where(frames == ref_frame)
    coldata = universe.atom.ix[universe.atom['frame'] == ref_frame, ['label', 'symbol']]
    coldata = (coldata['label'].astype(str) + '_' + coldata['symbol'].astype(str)).values
    groups = universe.atom.groupby('label')
    msd = np.empty((groups.ngroups, ), dtype='O')
    for i, (label, group) in enumerate(groups):
        xyz = group[['x', 'y', 'z']].values
        msd[i] = ((xyz - xyz[0])**2).sum(axis=1)
    df = pd.DataFrame.from_records(msd).T
    df.index = universe.frame.index.copy()
    df.columns = coldata
    return df
