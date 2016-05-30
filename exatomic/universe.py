# -*- coding: utf-8 -*-
'''
Universe (Container)
======================
Conceptually, a universe is a collection of independent (or related) frames
of a given system. For example, a universe may contain only a
single frame with the geometry of the molecule of interest, a set of
snapshot geometries obtained during the course of a geometry optimization (one
per frame), the same molecule's optimized geometry with each frame containing a
different level of theory, a properties calculation where each frame contains a
different small molecule, a molecular dynamics simulation with each frame
corresponding to a snaphot in time, etc.

The data architecture (see :func:`~exatomic.universe.Universe.data_architecture`)
is composed of a collection of dataframes that represent properties in terms of
concepts familiar to a computational chemist, such as atomic coordinates
(:class:`~exatomic.atom.Atom`), orbital energies (:class:`~exatomic.orbital.Orbital`),
orbital coefficients, basis set information, and fields (i.e. cube
files). Furthermore, aggregate data such as two body properties (bonds) and
atom collections (molecules) are available.

.. _exa: http://exa-analytics.github.io/website
'''
import pandas as pd
import numpy as np
from collections import OrderedDict
from sqlalchemy import Column, Integer, ForeignKey
from exa import Container
from exa.numerical import Field
from exatomic.widget import UniverseWidget
from exatomic.frame import minimal_frame, Frame
from exatomic.atom import Atom, ProjectedAtom, UnitAtom, VisualAtom
from exatomic.two import Two, PeriodicTwo
from exatomic.field import AtomicField
from exatomic.atom import compute_unit_atom as _cua
from exatomic.atom import compute_projected_atom as _cpa
from exatomic.atom import compute_visual_atom as _cva
from exatomic.two import max_frames_periodic as mfp
from exatomic.two import max_atoms_per_frame_periodic as mapfp
from exatomic.two import max_frames as mf
from exatomic.two import max_atoms_per_frame as mapf
from exatomic.two import compute_two_body as _ctb
from exatomic.two import compute_bond_count as _cbc
from exatomic.two import compute_projected_bond_count as _cpbc
from exatomic.molecule import Molecule
from exatomic.molecule import compute_molecule as _cm
from exatomic.molecule import compute_molecule_com as _cmcom
from exatomic.orbital import Orbital, MOMatrix
from exatomic.basis import SphericalGTFOrder, CartesianGTFOrder, BasisSetSummary
from exatomic.basis import lmap


class Universe(Container):
    '''
    A container for working with computational chemistry data.

    .. code-block:: Python

        u = Universe()               # Demo universe
        u.data_architecture()        # Universe's dataframes
        atom = XYZ('myfile.xyz')
        u = atom.to_universe()       # Universe from XYZ file
        u                            # Render universe
        atom = pd.read_csv('somefile.xyz', names=('symbol', 'x', 'y', 'z'))
        u = Universe(atom=atom)
        u.frame                      # Displays the universe's Frame dataframe
        small_uni = large_uni[::200] # Selects every 200th frame from the large_uni
        first_frame = large_uni[0]   # Create a universe for only the first frame
        last_frame = large_uni[-1]   # Create a universe for only the last frame
        specific = large_uni[[0, 10, 20]] # Create universe for 0th, 10th, and 20th frames (positional index)

    See Also:
        For a conceptual description of the universe, see the module's docstring.
    '''
    unid = Column(Integer, ForeignKey('container.pkid'), primary_key=True)
    frame_count = Column(Integer)
    _widget_class = UniverseWidget
    __mapper_args__ = {'polymorphic_identity': 'universe'}
    # The arguments here should match those of init (for dataframes)
    _df_types = OrderedDict([('frame', Frame), ('atom', Atom), ('two', Two),
                             ('unit_atom', UnitAtom), ('projected_atom', ProjectedAtom),
                             ('periodic_two', PeriodicTwo), ('molecule', Molecule),
                             ('visual_atom', VisualAtom), ('field', AtomicField),
                             ('orbital', Orbital), ('momatrix', MOMatrix),
                             ('spherical_gtf_order', SphericalGTFOrder),
                             ('cartesian_gtf_order', CartesianGTFOrder),
                             ('basis_set_summary', BasisSetSummary)])
    # Properties
    # ============
    # These are used to enable a simple API for performing (sometimes) complex
    # operations; it also facilitates lazy computation (computation only
    # when required)
    @property
    def frame(self):
        if not self._is('_frame'):
            if self._is('_atom'):
                self.compute_minimal_frame()
        return self._frame

    @property
    def atom(self):
        return self._atom

    @property
    def unit_atom(self):
        '''
        Updated atom table using only in-unit-cell positions.

        Note:
            This function returns a standard :class:`~pandas.DataFrame`
        '''
        if not self._is('_unit_atom'):
            self.compute_unit_atom()
        atom = self.atom.copy()
        atom.update(self._unit_atom)
        return Atom(atom)

    @property
    def visual_atom(self):
        '''
        Visually pleasing atomic coordinates (useful for periodic universes).
        '''
        if self.is_periodic:
            if self._visual_atom is None:
                self.compute_visual_atom()
            atom = self.atom.copy()
            atom.update(self._visual_atom)
            return atom
        else:
            return self.atom

    @property
    def projected_atom(self):
        '''
        Projected (unit) atom positions into a 3x3x3 supercell.
        '''
        if self._projected_atom is None:
            self.compute_projected_atom()
        return self._projected_atom

    @property
    def two(self):
        if not self._is('_two') and not self._is('_periodic_two'):
            self.compute_two_body()
        if self._is('_periodic_two'):
            return self._periodic_two
        return self._two

    @property
    def periodic_two(self):
        if not self._is('_periodic_two'):
            self.compute_two_body()
        return self._periodic_two

    @property
    def molecule(self):
        if not self._is('_molecule'):
            self.compute_molecule()
        return self._molecule

    @property
    def field(self):
        return self._field

    @property
    def orbital(self):
        return self._orbital

    @property
    def basis_set(self):
        return self._basis_set

    @property
    def momatrix(self):
        return self._momatrix

    @property
    def is_periodic(self):
        return self.frame.is_periodic

    @property
    def is_vc(self):
        return self.frame.is_vc

    @property
    def basis_set_summary(self):
        return self._basis_set_summary

    @property
    def spherical_gtf_order(self):
        if self._is('_spherical_gtf_order'):
            return self._spherical_gtf_order
        else:
            raise Exception('Compute spherical_gtf_order first!')

    @property
    def cartesian_gtf_order(self):
        if self._is('_cartesian_gtf_order'):
            return self._cartesian_gtf_order
        else:
            raise Exception('Compute cartesian_gtf_order first!')

    # Compute
    # ==============
    # Compute methods create and attach new dataframe objects to the container
    def compute_minimal_frame(self):
        '''
        Create a minimal frame using the atom table.
        '''
        self._frame = minimal_frame(self.atom)

    def compute_unit_atom(self):
        '''
        Compute the sparse unit atom dataframe.
        '''
        self._unit_atom = _cua(self)

    def compute_projected_atom(self):
        '''
        Compute the projected supercell from the unit atom coordinates.
        '''
        self._projected_atom = _cpa(self)

    def compute_bond_count(self):
        '''
        Compute the bond count and update the atom table.

        Returns:
            bc (:class:`~pandas.Series`): :class:`~exatomic.atom.Atom` bond counts
            pbc (:class:`~pandas.Series`): :class:`~exatomic.atom.PeriodicAtom` bond counts

        Note:
            If working with a periodic universe, the projected atom table will
            also be updated; an index of minus takes the usual convention of
            meaning not applicable or not calculated.
        '''
        self.atom['bond_count'] = _cbc(self)
        self.atom['bond_count'] = self.atom['bond_count'].fillna(0).astype(np.int64)
        self.atom['bond_count'] = self.atom['bond_count'].astype('category')

    def compute_projected_bond_count(self):
        '''
        See Also:
            :func:`~exatomic.two.compute_projected_bond_count`
        '''
        self.projected_atom['bond_count'] = _cpbc(self)
        self.projected_atom['bond_count'] = self.projected_atom['bond_count'].fillna(-1).astype(np.int64)
        self.projected_atom['bond_count'] = self.projected_atom['bond_count'].astype('category')

    def compute_molecule(self, com=False):
        '''
        Compute the molecule table.
        '''
        if com:
            self._molecule = _cm(self)
            self.compute_visual_atom()
            self._molecule = Molecule(pd.concat((self._molecule, _cmcom(self)), axis=1))
        else:
            self._molecule = _cm(self)

    def compute_spherical_gtf_order(self, ordering_func):
        '''
        Compute the spherical Gaussian type function ordering dataframe.
        '''
        lmax = universe.basis_set['shell'].map(lmap).max()
        self._spherical_gtf_order = SphericalGTFOrder.from_lmax_order(lmax, ordering_func)

    def compute_cartesian_gtf_order(self, ordering_func):
        '''
        Compute the cartesian Gaussian type function ordering dataframe.
        '''
        lmax = universe.basis_set['shell'].map(lmap).max()
        self._cartesian_gtf_order = SphericalGTFOrder.from_lmax_order(lmax, ordering_func)

    def compute_two_body(self, *args, truncate_projected=True, **kwargs):
        '''
        Compute two body properties for the current universe.

        For arguments see :func:`~exatomic.two.get_two_body`. Note that this
        operation (like all compute) operations are performed in place.

        Args:
            truncate_projected (bool): Applicable to periodic universes - decreases the size of the projected atom table
        '''
        if self.is_periodic:
            self._periodic_two = _ctb(self, *args, **kwargs)
            if truncate_projected:
                self.truncate_projected_atom()
        else:
            self._two = _ctb(self, *args, **kwargs)

    def compute_visual_atom(self):
        '''
        Create visually pleasing coordinates (useful for periodic universes).
        '''
        self._visual_atom = _cva(self)

    def append_dataframe(self, df):
        '''
        Attach a new dataframe or append the data of a given dataframe to the
        appropriate existing dataframe.
        '''
        raise NotImplementedError()

    def append_field(self, field, frame=None, field_values=None):
        '''
        Add (insert/concat) field dataframe to the current universe.

        Args:
            field: Complete field (instance of :class:`~exa.numerical.Field`) to add or field dimensions dataframe
            frame (int): Frame index where to insert/concat
            field_values: Field values list (if field is incomplete)
        '''
        if isinstance(frame, int) or isinstance(frame, np.int64) or isinstance(frame, np.int32):
            if frame not in self.frame.index:
                raise IndexError('frame {} does not exist in the universe?'.format(frame))
            field['frame'] = frame
        df = self._reconstruct_field('field', field, field_values)
        if self._field is None:
            self._field = df
        else:
            cls = self._df_types['field']
            values = self._field.field_values + df.field_values
            self._field._revert_categories()
            df._revert_categories()
            df = pd.concat((pd.DataFrame(self._field), pd.DataFrame(df)), ignore_index=True)
            df.reset_index(inplace=True, drop=True)
            self._field = cls(values, df)
            self._field._set_categories()
        self._traits_need_update = True

    def classify_molecules(self, *args, **kwargs):
        '''
        Add classifications (of any form) for molecules.

        .. code-block:: Python

            universe.classify_molecules(('Na', 'solute'), ('H(2)O(1)', 'solvent'))

        Args:
            \*classifiers: ('identifier', 'classification', exact)


        Warning:
            Will attempt to compute molecules if they haven't been computed.
        '''
        self.molecule.classify(*args, **kwargs)

    def slice_by_molecules(self, identifier):
        '''
        String, list of string, index, list of indices, slice
        '''
        raise NotImplementedError()

    def truncate_projected_atom(self):
        '''
        When first generated, the projected_atom table contains many atomic
        coordinates that are not used when computing two body properties. This
        function will truncate this table, keeping only useful coordinates.
        Projected coordinates can always be generated using
        :func:`~exatomic.atom.compute_projected_atom`.
        '''
        pa = self.periodic_two['prjd_atom0'].astype(np.int64)
        pa = pa.append(self.periodic_two['prjd_atom1'].astype(np.int64))
        self._projected_atom = ProjectedAtom(self._projected_atom[self._projected_atom.index.isin(pa)])

    def _slice_by_mids(self, molecule_indices):
        '''
        '''
        raise NotImplementedError()

    def _other_bytes(self):
        '''
        Field values are not captured by the df_bytes so add them here.
        '''
        field_bytes = 0
        if self._is('_field'):
            for field_value in self.field_values:
                field_bytes += field_value.memory_usage()
        return field_bytes

    def _custom_container_traits(self):
        '''
        Create custom traits using multiple (related) dataframes.
        '''
        traits = {}
        if self.display['atom_table'] == 'visual':
            traits.update(self.visual_atom._custom_trait_creator())
        elif self.display['atom_table'] == 'unit':
            traits.update(self.unit_atom._custom_trait_creator())
        else:
            traits.update(self.atom._custom_trait_creator())
        if self._is('_two'):
            traits.update(self.two._get_bond_traits(self.atom))
        elif self._is('_periodic_two'):
            self.projected_atom['label'] = self.projected_atom['atom'].map(self.atom['label'])
            traits.update(self.two._get_bond_traits(self.projected_atom))
            del self.projected_atom['label']
        return traits

    def __len__(self):
        return len(self.frame) if self._is('_frame') else 0

    def __init__(self, frame=None, atom=None, two=None, field=None,
                 field_values=None, unit_atom=None, projected_atom=None,
                 periodic_two=None, molecule=None, visual_atom=None, orbital=None,
                 momatrix=None, basis_set=None, spherical_gtf_order=None,
                 cartesian_gtf_order=None, basis_set_summary=None, **kwargs):
        '''
        The arguments field and field_values are paired: field is the dataframe
        containing all of the dimensions of the scalar or vector fields and
        field_values is the list of series or dataframe objects that contain
        the magnitudes with list position corresponding to the field dataframe
        index.

        The above approach is only used when loading a universe from a file; in
        general only the (appropriately typed) field argument (already
        containing the field_values - see :mod:`~exatomic.field`) is needed to
        correctly attach fields.
        '''
        self._frame = self._enforce_df_type('frame', frame)
        self._atom = self._enforce_df_type('atom', atom)
        self._field = self._reconstruct_field('field', field, field_values)
        self._two = self._enforce_df_type('two', two)
        self._unit_atom = self._enforce_df_type('unit_atom', unit_atom)
        self._projected_atom = self._enforce_df_type('projected_atom', projected_atom)
        self._periodic_two = self._enforce_df_type('periodic_two', periodic_two)
        self._molecule = self._enforce_df_type('molecule', molecule)
        self._visual_atom = self._enforce_df_type('visual_atom', visual_atom)
        self._orbital = self._enforce_df_type('orbital', orbital)
        self._momatrix = self._enforce_df_type('momatrix', momatrix)
        self._spherical_gtf_order = self._enforce_df_type('spherical_gtf_order', spherical_gtf_order)
        self._cartesian_gtf_order = self._enforce_df_type('cartesian_gtf_order', cartesian_gtf_order)
        self._basis_set_summary = self._enforce_df_type('basis_set_summary', basis_set_summary)
        self._basis_set = basis_set
        super().__init__(**kwargs)
        # For smaller systems it is advantageous (for visualization purposes)
        # to compute two body properties (i.e. bonds). This is an exception to
        # the lazy computation philsophy.
        self.display = {'atom_table': 'atom'}
        ma = self.frame['atom_count'].max() if self._is('_atom') else 0
        nf = len(self)
        if ma == 0 and nf == 0:
            self.name = 'TestUniverse'
            self._widget.width = 950
            self._widget.gui_width = 350
            self._update_traits()
            self._traits_need_update = False
        elif self.is_periodic and ma < mapfp and nf < mfp and self._atom is not None:
            if self._periodic_two is None:
                pass
#                self.compute_two_body()
#            self._update_traits()
            self._traits_need_update = False
        elif not self.is_periodic and ma < mapf and nf < mf and self._atom is not None:
#            if self._two is None:
#                self.compute_two_body()
#            self._update_traits()
            self._traits_need_update = False