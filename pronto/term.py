# coding: utf-8
"""
pronto.term
===========

This module defines the classes Term and TermList.
"""

import six

from pronto.relationship import Relationship


class Term(object):
    """ An ontology term.

    Examples:

        >>> from pronto import *
        >>> new_term = Term('TR:001', 'new term', 'a new term')
        >>> linked_term = Term('TR:002', 'other new', 'another term',
        ...                    { Relationship('is_a'): 'TR:001'})

        >>> ms = Ontology('https://raw.githubusercontent.com/'
        ...               'HUPO-PSI/psi-ms-CV/master/psi-ms.obo')
        >>> type(ms['MS:1000015'])
        <class 'pronto.term.Term'>


    """

    def __init__(self, tid, name, desc='', relations=None, other=None):
        """

        Parameters:
            tid (str): the Term id (e.g. MS:1000031)
            name (str): the name of the Term in human language
            desc (str): a description of the Term
            relations (dict): a dictionary containing the other
                terms the Term is in a relationship with.
            other (dict): other information about the term

        """
        self.id = tid
        self.name = name
        self.desc = desc
        self.relations = relations or {}
        self.other = other or {}
        self._rchildren  = {}
        self._rparents = {}
        self._children = None
        self._parents = None

    def __repr__(self):
        return "<{}: {}>".format(self.id, self.name)

    @property
    def parents(self):
        """The parents of the Term.

        Returns:
            :obj:`pronto.TermList`:
            a TermList containing all parents of the Term
            (other terms with which this Term has a "bottomup"
            relationship)

        Example:

            >>> for p in ms['MS:1000532'].parents: print(p.desc)
            "Thermo Finnigan software for data acquisition and analysis." [PSI:MS]
            "Acquisition software." [PSI:MS]
            "Analysis software." [PSI:MS]
            "Data processing software." [PSI:MS]

        """

        if self._parents is None:
            bottomups = tuple(Relationship.bottomup())

            self._parents = TermList()
            self._parents.extend(
                [ other
                    for rship,others in six.iteritems(self.relations)
                        for other in others
                            if rship in bottomups
                ]

            )

        return self._parents

    @property
    def children(self):
        """The children of the Term.

        Returns:
            :obj:`pronto.TermList`:

            a TermList containing all parents of the Term
            (other terms with which this Term has a "topdown"
            relationship)

        Example:

            >>> ms['MS:1000452'].children
            [<MS:1000530: file format conversion>, <MS:1000543: data processing action>]

        """

        if self._children is None:

            topdowns = tuple(Relationship.topdown())
            self._children = TermList()
            self._children.extend(
                [ other
                    for rship,others in six.iteritems(self.relations)
                        for other in others
                            if rship in topdowns
                ]

            )

        return self._children



            #for rship in Relationship.topdown():
            #    if rship in self.relations:
            #        self._children.extend(self.relations[rship])
        #return self._children

    @property
    def obo(self):
        """Displays the term as an obo Term entry

        Example:

            >>> print(ms['MS:1000031'].obo)
            [Term]
            id: MS:1000031
            name: instrument model
            def: "Instrument model name not including the vendor's name." [PSI:MS]
            relationship: part_of: MS:1000463 ! instrument

        """



        obo =  "".join([ '[Term]', '\n',
        #obo +=
                         'id: ', self.id, '\n',

        #obo +=
                         'name: ', self.name if self.name is not None else '', '\n'])

        if self.desc:
            obo = "".join([obo, 'def: ', self.desc, '\n'])

        # add more bits of information
        for k,v in six.iteritems(self.other):
            if isinstance(v, list):
                for x in v:
                    obo = "".join([obo, k, ': ', x, '\n'])
            else:
                obo = "".join([obo,k, ': ', v, '\n'])

        # add relationships (only bottom up ones)

        for relation in Relationship.bottomup():
            try:
                for companion in self.relations[relation]:

                    if relation is not Relationship('is_a'):
                        obo = "".join([obo, 'relationship: '])
                    obo = "".join([obo, relation.obo_name, ': '])

                    try:
                        obo = "".join([obo, companion.id, ' ! ', companion.name, '\n'])
                    except AttributeError:
                        obo = "".join([obo,companion, '\n'])

            except KeyError:
                continue

        return obo.rstrip()

    @property
    def __deref__(self):
        """A dereferenced relations dictionary only contains other Terms id
        to avoid circular references when creating a json.
        """
        return {
            'id': self.id,
            'name': self.name,
            'other': self.other,
            'desc': self.desc,
            'relations': {k.obo_name:v.id for k,v in six.iteritems(self.relations)}
         }

    def __getstate__(self):

        return (
            self.id,
            self.name,
            tuple((k,v) for k,v in six.iteritems(self.other)),
            self.desc,
            tuple((k.obo_name,v.id) for k,v in six.iteritems(self.relations)),
        )

    def __setstate__(self, state):

        self.id = state[0]
        self.name = state[1]
        self.other = {k:v for (k,v) in state[2]}
        self.desc = state[3]
        self.relations = {Relationship(k):v for k,v in state[4]}

    def _empty_cache(self):
        """
        Empties the cache of the Term's memoized functions.
        """
        self._children, self._parents = None, None
        self._rchildren, self._rparents = {}, {}

    def rchildren(self, level=-1, intermediate=True):
        """Create a recursive list of children.

        Note that the :param:`intermediate` can be used to include every
        child to the returned list, not only the most nested ones.

        Parameters:
            level (int): The depth level to continue fetching children from
                (default is -1, to get children to the utter depths)
            intermediate (bool): Also include the intermediate children
                (default is True)

        Returns:
            :obj:`pronto.TermList`:
            The recursive children of the Term following the parameters

        """
        try:
            return self._rchildren[(level, intermediate)]

        except KeyError:

            rchildren = []

            if self.children and level:

                if intermediate or level==1:
                    rchildren.extend(self.children)

                for child in self.children:
                    rchildren.extend(child.rchildren(level=level-1,
                                                     intermediate=intermediate))

            rchildren = TermList(set(rchildren))
            self._rchildren[(level, intermediate)] = rchildren
            return rchildren

    def rparents(self, level=-1, intermediate=True):
        """Create a recursive list of children.

        Note that the :param:`intermediate` can be used to include every
        parents to the returned list, not only the most nested ones.

        Parameters:
            level (int): The depth level to continue fetching parents from
                (default is -1, to get parents to the utter depths)
            intermediate (bool): Also include the intermediate parents
                (default is True)

        Returns:
            :obj:`pronto.TermList`:
            The recursive children of the Term following the parameters

        """
        try:
            return self._rparents[(level, intermediate)]

        except KeyError:

            rparents = []

            if self.parents and level:

                if intermediate or level==1:
                    rparents.extend(self.parents)

                for parent in self.parents:
                    rparents.extend(parent.rparents(level=level-1,
                                                     intermediate=intermediate))

            rparents = TermList(set(rparents))
            self._rparents[(level, intermediate)] = rparents
            return rparents


class TermList(list):
    """A list of Terms.

    TermList behaves exactly like a list, except it contains shortcuts to
    generate lists of terms' attributes.

    Example:
        >>> from pronto import *
        >>> nmr = Ontology('http://nmrml.org/cv/v1.0.rc1/nmrCV.owl')
        >>> type(nmr['NMR:1000031'].children)
        <class 'pronto.term.TermList'>

        >>> nmr['NMR:1000031'].children.id
        ['NMR:1000122', 'NMR:1000156', 'NMR:1000157', 'NMR:1000489']
        >>> nmr['NMR:1400014'].relations[Relationship('is_a')]
        [<NMR:1400011: cardinal part of NMR instrument>]


    .. tip::
        It is also possible to call Term methods on a TermList to
        create a set of terms::

            >>> nmr['NMR:1000031'].rchildren(3, False).rparents(3, False).id
            ['NMR:1000031']

    """

    def __init__(self, *elements):
        """
        """
        list.__init__(self, *elements)
        self._check_content()

    def _check_content(self):
        try:
            [ term.id for term in self ]
        except AttributeError:
            raise TypeError('TermList can only contain Terms.')

        #for term in self:
        #    if not isinstance(term, Term):
        #        raise TypeError('TermList can only contain Terms.')

    # def __getattr__(self, attr, *args, **kwargs):
    #     if attr in ('children', 'parents'):
    #         return TermList( [ y for x in self for y in getattr(x, attr)] )
    #     elif attr in ('rparents', 'rchildren'):
    #         #: we create a new method to allow the user
    #         #: to use, for instance, ``x.rchildren(3).rparents(2)``
    #         #: (this actually behaves as if you mapped the method
    #         #: on all terms of the TermList)

    #         #def mapped(level=-1, intermediate=True):
    #         #    t = TermList(set([ y for x in self
    #         #            for y in getattr(x, attr)(level, intermediate) ]))
    #         #    return t
    #         #return mapped

    #         return self.__dict__[attr]

    #     elif attr in ('id', 'name', 'desc', 'other', 'obo'):
    #         return [getattr(x, attr) for x in self]
    #     else:
    #         getattr(list, attr)

    def rparents(self, level=-1, intermediate=True):
        return TermList(set(
            [y for x in self for y in x.rparents(level, intermediate)]
        ))

    def rchildren(self, level=-1, intermediate=True):
        return TermList(set(
            [y for x in self for y in x.rchildren(level, intermediate)]
        ))

    @property
    def children(self):
        return TermList( [ y for x in self for y in x.children] )

    @property
    def parents(self):
        return TermList( [ y for x in self for y in x.parents] )

    #elif attr in ('id', 'name', 'desc', 'other', 'obo'):
    #         return [getattr(x, attr) for x in self]

    @property
    def id(self):
        return [x.id for x in self]

    @property
    def name(self):
        return [x.name for x in self]

    @property
    def desc(self):
        return [x.desc for x in self]

    @property
    def other(self):
        return [x.other for x in self]

    @property
    def obo(self):
        return [x.obo for x in self]

    def __getstate__(self):
        return (x for x in self)

    def __setstate__(self, state):
        self.extend(state)

    def __contains__(self, term):
        """
        Todo:
            write doc & test
        """
        return term in self.id or any(t for t in self if t==term)


