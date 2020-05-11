from typing import List

import stringcase
from bmt import Toolkit
from cachetools import LRUCache
from prefixcommons.curie_util import contract_uri
from prefixcommons.curie_util import expand_uri

from kgx.config import get_jsonld_context

toolkit = None
curie_lookup_service = None
cache = None


def camelcase_to_sentencecase(s: str) -> str:
    """
    Convert CamelCase to sentence case.

    Parameters
    ----------
    s: str
        Input string in CamelCase

    Returns
    -------
    str
        a normal string

    """
    return stringcase.sentencecase(s).lower()

def snakecase_to_sentencecase(s: str) -> str:
    """
    Convert snake_case to sentence case.

    Parameters
    ----------
    s: str
        Input string in snake_case

    Returns
    -------
    str
        a normal string

    """
    return stringcase.sentencecase(s).lower()

def sentencecase_to_snakecase(s: str) -> str:
    """
    Convert sentence case to snake_case.

    Parameters
    ----------
    s: str
        Input string in sentence case

    Returns
    -------
    str
        a normal string

    """
    return stringcase.snakecase(s).lower()


def contract(uri: str, prefix_maps: List[dict] = None, fallback: bool = True) -> str:
    """
    Contract a given URI to a CURIE, based on mappings from `prefix_maps`.
    If no prefix map is provided then will use defaults from prefixcommons-py.

    Parameters
    ----------
    uri: str
        A URI
    prefix_maps: List[dict]
        A list of prefix maps to use for mapping
    fallback: bool
        Determines whether to fallback to default prefix mappings, as determined
        by `prefixcommons.curie_util`, when URI prefix is not found in `prefix_maps`.

    Returns
    -------
    str
        A CURIE corresponding to the URI

    """
    curie = None
    default_curie_maps = [get_jsonld_context('monarch_context'), get_jsonld_context('obo_context')]
    if prefix_maps:
        curie_list = contract_uri(uri, prefix_maps)
        if len(curie_list) == 0 and fallback:
            curie_list = contract_uri(uri, default_curie_maps)
            if len(curie_list) != 0:
                curie = curie_list[0]
        else:
            curie = curie_list[0]
    else:
        curie_list = contract_uri(uri, default_curie_maps)
        if len(curie_list) > 0:
            curie = curie_list[0]

    return curie


def expand(curie: str, prefix_maps: List[dict] = None, fallback: bool = True) -> str:
    """
    Expand a given CURIE to an URI, based on mappings from `prefix_map`.

    Parameters
    ----------
    curie: str
        A CURIE
    prefix_maps: List[dict]
        A list of prefix maps to use for mapping
    fallback: bool
        Determines whether to fallback to default prefix mappings, as determined
        by `prefixcommons.curie_util`, when CURIE prefix is not found in `prefix_maps`.

    Returns
    -------
    str
        A URI corresponding to the CURIE

    """
    default_curie_maps = [get_jsonld_context('monarch_context'), get_jsonld_context('obo_context')]
    if prefix_maps:
        uri = expand_uri(curie, prefix_maps)
        if uri == curie and fallback:
            uri = expand_uri(curie, default_curie_maps)
    else:
        uri = expand_uri(curie, default_curie_maps)

    return uri


def get_toolkit() -> Toolkit:
    """
    Get an instance of bmt.Toolkit
    If there no instance defined, then one is instantiated and returned.

    Returns
    -------
    bmt.Toolkit
        an instance of bmt.Toolkit

    """
    global toolkit
    if toolkit is None:
        toolkit = Toolkit()

    return toolkit

def generate_edge_key(s: str, edge_label: str, o: str) -> str:
    """
    Generates an edge key based on a given subject, edge_label and object.

    Parameters
    ----------
    s: str
        Subject
    edge_label: str
        Edge label
    o: str
        Object

    Returns
    -------
    str
        Edge key as a string

    """
    return '{}-{}-{}'.format(s, edge_label, o)

def get_biolink_mapping(category):
    """
    Get a BioLink Model mapping for a given ``category``.

    Parameters
    ----------
    category: str
        A category for which there is a mapping in BioLink Model

    Returns
    -------
    str
        A BioLink Model class corresponding to ``category``

    """
    global toolkit
    element = toolkit.get_element(category)
    if element is None:
        element = toolkit.get_element(snakecase_to_sentencecase(category))
    return element

def get_curie_lookup_service():
    """
    Get an instance of kgx.curie_lookup_service.CurieLookupService

    Returns
    -------
    kgx.curie_lookup_service.CurieLookupService
        An instance of ``CurieLookupService``

    """
    global curie_lookup_service
    if curie_lookup_service is None:
        from kgx.curie_lookup_service import CurieLookupService
        curie_lookup_service = CurieLookupService()
    return curie_lookup_service

def get_cache(maxsize=10000):
    """
    Get an instance of cachetools.cache

    Parameters
    ----------
    maxsize: int
        The max size for the cache (``10000``, by default)

    Returns
    -------
    cachetools.cache
        An instance of cachetools.cache

    """
    global cache
    if cache is None:
        cache = LRUCache(maxsize)
    return cache
