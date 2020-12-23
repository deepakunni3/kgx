import re
import time
import uuid
from typing import List, Dict, Set, Optional, Any, Union
import stringcase
from biolinkml.meta import TypeDefinitionName, ElementName, SlotDefinition, ClassDefinition, TypeDefinition, Element
from bmt import Toolkit
from cachetools import LRUCache
from prefixcommons.curie_util import contract_uri
from prefixcommons.curie_util import expand_uri

from kgx.config import get_jsonld_context, get_logger, get_config
from kgx.graph.base_graph import BaseGraph

toolkit = None
curie_lookup_service = None
cache = None

log = get_logger()

is_property_multivalued = {
    'biolink:id': False,
    'biolink:subject': False,
    'biolink:object': False,
    'biolink:predicate': False,
    'biolink:description': False,
    'biolink:synonym': True,
    'biolink:in_taxon': False,
    'biolink:same_as': True,
    'biolink:name': False,
    'biolink:has_evidence': False,
    'biolink:provided_by': True,
    'biolink:category': True,
    'biolink:publications': True,
    'biolink:type': False,
    'biolink:relation': False
}

CORE_NODE_PROPERTIES = {'biolink:id', 'biolink:name'}
CORE_EDGE_PROPERTIES = {'biolink:id', 'biolink:subject', 'biolink:predicate', 'biolink:object', 'biolink:relation'}


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
        string in sentence case form

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
        string in sentence case form

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
        string in snake_case form

    """
    return stringcase.snakecase(s).lower()


def sentencecase_to_camelcase(s: str) -> str:
    """
    Convert sentence case to CamelCase.

    Parameters
    ----------
    s: str
        Input string in sentence case

    Returns
    -------
    str
        string in CamelCase form

    """
    return stringcase.pascalcase(stringcase.snakecase(s))


def format_biolink_category(s: str) -> str:
    """
    Convert a sentence case Biolink category name to
    a proper Biolink CURIE with the category itself
    in CamelCase form.

    Parameters
    ----------
    s: str
        Input string in sentence case

    Returns
    -------
    str
        a proper Biolink CURIE
    """
    if re.match("biolink:.+", s):
        return s
    else:
        formatted = sentencecase_to_camelcase(s)
        return f"biolink:{formatted}"


def format_biolink_slots(s: str) -> str:
    if re.match("biolink:.+", s):
        return s
    else:
        formatted = sentencecase_to_snakecase(s)
        return f"biolink:{formatted}"


def contract(uri: str, prefix_maps: Optional[List[Dict]] = None, fallback: bool = True) -> str:
    """
    Contract a given URI to a CURIE, based on mappings from `prefix_maps`.
    If no prefix map is provided then will use defaults from prefixcommons-py.

    This method will return the URI as the CURIE if there is no mapping found.

    Parameters
    ----------
    uri: str
        A URI
    prefix_maps: Optional[List[Dict]]
        A list of prefix maps to use for mapping
    fallback: bool
        Determines whether to fallback to default prefix mappings, as determined
        by `prefixcommons.curie_util`, when URI prefix is not found in `prefix_maps`.

    Returns
    -------
    str
        A CURIE corresponding to the URI

    """
    curie = uri
    default_curie_maps = [get_jsonld_context('monarch_context'), get_jsonld_context('obo_context')]
    if prefix_maps:
        curie_list = contract_uri(uri, prefix_maps)
        if len(curie_list) == 0:
            if fallback:
                curie_list = contract_uri(uri, default_curie_maps)
                if curie_list:
                    curie = curie_list[0]
        else:
            curie = curie_list[0]
    else:
        curie_list = contract_uri(uri, default_curie_maps)
        if len(curie_list) > 0:
            curie = curie_list[0]

    return curie


def expand(curie: str, prefix_maps: Optional[List[dict]] = None, fallback: bool = True) -> str:
    """
    Expand a given CURIE to an URI, based on mappings from `prefix_map`.

    This method will return the CURIE as the IRI if there is no mapping found.

    Parameters
    ----------
    curie: str
        A CURIE
    prefix_maps: Optional[List[dict]]
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


def get_toolkit(schema: Optional[str] = None) -> Toolkit:
    """
    Get an instance of bmt.Toolkit
    If there no instance defined, then one is instantiated and returned.
    """
    global toolkit
    if toolkit is None:
        if not schema:
            config = get_config()
            schema = config['biolink-model']
        toolkit = Toolkit(schema=schema)
    return toolkit


def generate_edge_key(s: str, edge_predicate: str, o: str) -> str:
    """
    Generates an edge key based on a given subject, predicate, and object.

    Parameters
    ----------
    s: str
        Subject
    edge_predicate: str
        Edge label
    o: str
        Object

    Returns
    -------
    str
        Edge key as a string

    """
    return '{}-{}-{}'.format(s, edge_predicate, o)


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


def current_time_in_millis():
    """
    Get current time in milliseconds.

    Returns
    -------
    int
        Time in milliseconds

    """
    return int(round(time.time() * 1000))


def get_prefix_prioritization_map() -> Dict[str, List]:
    """
    Get prefix prioritization map as defined in Biolink Model.

    Returns
    -------
    Dict[str, List]

    """
    toolkit = get_toolkit()
    prefix_prioritization_map = {}
    # TODO: Lookup via Biolink CURIE should be supported in bmt
    descendants = toolkit.get_descendants('named thing')
    descendants.append('named thing')
    for d in descendants:
        element = toolkit.get_element(d)
        if element and 'id_prefixes' in element:
            prefixes = element.id_prefixes
            key = format_biolink_category(element.name)
            prefix_prioritization_map[key] = prefixes
    return prefix_prioritization_map


def get_biolink_element(name) -> Optional[Element]:
    """
    Get Biolink element for a given name, where name can be a class, slot, or relation.

    Parameters
    ----------
    name: str
        The name

    Returns
    -------
    Optional[biolinkml.meta.Element]
        An instance of biolinkml.meta.Element

    """
    toolkit = get_toolkit()
    element = toolkit.get_element(name)
    return element


def get_biolink_ancestors(name: str):
    """
    Get ancestors for a given Biolink class.

    Parameters
    ----------
    name: str

    Returns
    -------
    List
        A list of ancestors

    """
    toolkit = get_toolkit()
    ancestors = toolkit.get_ancestors(name, formatted=True)
    return ancestors


def get_biolink_property_types() -> Dict:
    """
    Get all Biolink property types.
    This includes both node and edges properties.

    Returns
    -------
    Dict
        A dict containing all Biolink property and their types

    """
    toolkit = get_toolkit()
    types = {}
    node_properties = toolkit.get_all_node_properties(formatted=True)
    edge_properties = toolkit.get_all_edge_properties(formatted=True)

    for p in node_properties:
        property_type = get_type_for_property(p)
        types[p] = property_type

    for p in edge_properties:
        property_type = get_type_for_property(p)
        types[p] = property_type

    # TODO: this should be moved to biolink model
    types['biolink:predicate'] = 'uriorcurie'
    types['biolink:edge_label'] = 'uriorcurie'
    return types


def get_type_for_property(p: str) -> str:
    """
    Get type for a property.

    TODO: Move this to biolink-model-toolkit

    Parameters
    ----------
    p: str

    Returns
    -------
    str
        The type for a given property

    """
    toolkit = get_toolkit()
    e = toolkit.get_element(p)
    t = 'xsd:string'
    if e:
        if isinstance(e, ClassDefinition):
            t = "uriorcurie"
        elif isinstance(e, TypeDefinition):
            t = e.uri
        else:
            r = e.range
            if isinstance(r, SlotDefinition):
                t = r.range
                t = get_type_for_property(t)
            elif isinstance(r, TypeDefinitionName):
                t = get_type_for_property(r)
            elif isinstance(r, ElementName):
                t = get_type_for_property(r)
            else:
                t = "xsd:string"
    return t


def prepare_data_dict(d1: Dict, d2: Dict, preserve: bool = True) -> Dict:
    """
    Given two dict objects, make a new dict object that is the intersection of the two.

    If a key is known to be multivalued then it's value is converted to a list.
    If a key is already multivalued then it is updated with new values.
    If a key is single valued, and a new unique value is found then the existing value is
    converted to a list and the new value is appended to this list.

    Parameters
    ----------
    d1: Dict
        Dict object
    d2: Dict
        Dict object
    preserve: bool
        Whether or not to preserve values for conflicting keys

    Returns
    -------
    Dict
        The intersection of d1 and d2

    """
    new_data = {}
    for key, value in d2.items():
        if isinstance(value, (list, set, tuple)):
            new_value = [x for x in value]
        else:
            new_value = value

        if key in is_property_multivalued:
            if is_property_multivalued[key]:
                # value for key is supposed to be multivalued
                if key in d1:
                    # key is in data
                    if isinstance(d1[key], (list, set, tuple)):
                        # existing key has value type list
                        new_data[key] = d1[key]
                        if isinstance(new_value, (list, set, tuple)):
                            new_data[key] += [x for x in new_value if x not in new_data[key]]
                        else:
                            if new_value not in new_data[key]:
                                new_data[key].append(new_value)
                    else:
                        if key in CORE_NODE_PROPERTIES or key in CORE_EDGE_PROPERTIES:
                            log.debug(f"cannot modify core property '{key}': {d2[key]} vs {d1[key]}")
                        else:
                            # existing key does not have value type list; converting to list
                            new_data[key] = [d1[key]]
                            if isinstance(new_value, (list, set, tuple)):
                                new_data[key] += [x for x in new_value if x not in new_data[key]]
                            else:
                                if new_value not in new_data[key]:
                                    new_data[key].append(new_value)
                else:
                    # key is not in data; adding
                    if isinstance(new_value, (list, set, tuple)):
                        new_data[key] = [x for x in new_value]
                    else:
                        new_data[key] = [new_value]
            else:
                # key is not multivalued; adding/replacing as-is
                if key in d1:
                    if isinstance(d1[key], (list, set, tuple)):
                        new_data[key] = d1[key]
                        if isinstance(new_value, (list, set, tuple)):
                            new_data[key] += [x for x in new_value]
                        else:
                            new_data[key].append(new_value)
                    else:
                        if key in CORE_NODE_PROPERTIES or key in CORE_EDGE_PROPERTIES:
                            log.debug(f"cannot modify core property '{key}': {d2[key]} vs {d1[key]}")
                        else:
                            if preserve:
                                new_data[key] = [d1[key]]
                                if isinstance(new_value, (list, set, tuple)):
                                    new_data[key] += [x for x in new_value if x not in new_data[key]]
                                else:
                                    new_data[key].append(new_value)
                            else:
                                new_data[key] = new_value
                else:
                    new_data[key] = new_value
        else:
            # treating key as multivalued
            if key in d1:
                # key is in data
                if key in CORE_NODE_PROPERTIES or key in CORE_EDGE_PROPERTIES:
                    log.debug(f"cannot modify core property '{key}': {d2[key]} vs {d1[key]}")
                else:
                    if isinstance(d1[key], (list, set, tuple)):
                        # existing key has value type list
                        new_data[key] = d1[key]
                        if isinstance(new_value, (list, set, tuple)):
                            new_data[key] += [x for x in new_value if x not in new_data[key]]
                        else:
                            new_data[key].append(new_value)
                    else:
                        # existing key does not have value type list; converting to list
                        if preserve:
                            new_data[key] = [d1[key]]
                            if isinstance(new_value, (list, set, tuple)):
                                new_data[key] += [x for x in new_value if x not in new_data[key]]
                            else:
                                new_data[key].append(new_value)
                        else:
                            new_data[key] = new_value
            else:
                new_data[key] = new_value

    for key, value in d1.items():
        if key not in new_data:
            new_data[key] = value
    return new_data


def apply_filters(graph: BaseGraph, node_filters: Dict[str, Union[str, Set]], edge_filters: Dict[str, Union[str, Set]]) -> None:
    """
    Apply filters to graph and remove nodes and edges that
    do not pass given filters.

    Parameters
    ----------
    graph: kgx.graph.base_graph.BaseGraph
        The graph
    node_filters: Dict[str, Union[str, Set]]
        Node filters
    edge_filters: Dict[str, Union[str, Set]]
        Edge filters

    """
    apply_node_filters(graph, node_filters)
    apply_edge_filters(graph, edge_filters)


def apply_node_filters(graph: BaseGraph, node_filters: Dict[str, Union[str, Set]]) -> None:
    """
    Apply filters to graph and remove nodes that do not pass given filters.

    Parameters
    ----------
    graph: kgx.graph.base_graph.BaseGraph
        The graph
    node_filters: Dict[str, Union[str, Set]]
        Node filters

    """
    nodes_to_remove = []
    for node, node_data in graph.nodes(data=True):
        pass_filter = True
        for k, v in node_filters.items():
            if k == 'biolink:category':
                if not any(x in node_data[k] for x in v):
                    pass_filter = False
        if not pass_filter:
            nodes_to_remove.append(node)

    for node in nodes_to_remove:
        # removing node that fails category filter
        log.debug(f"Removing node {node}")
        graph.remove_node(node)


def apply_edge_filters(graph: BaseGraph, edge_filters: Dict[str, Union[str, Set]]) -> None:
    """
    Apply filters to graph and remove edges that do not pass given filters.

    Parameters
    ----------
    graph: kgx.graph.base_graph.BaseGraph
        The graph
    edge_filters: Dict[str, Union[str, Set]]
        Edge filters

    """
    edges_to_remove = []
    for subject_node, object_node, key, data in graph.edges(keys=True, data=True):
        pass_filter = True
        for k, v in edge_filters.items():
            if k == 'biolink:predicate':
                if data[k] not in v:
                    pass_filter = False
            elif k == 'biolink:relation':
                if data[k] not in v:
                    pass_filter = False
        if not pass_filter:
            edges_to_remove.append((subject_node, object_node, key))

    for edge in edges_to_remove:
        # removing edge that fails edge filters
        log.debug(f"Removing edge {edge}")
        graph.remove_edge(edge[0], edge[1], edge[2])


def generate_uuid():
    """
    Generates a UUID.

    Returns
    -------
    str
        A UUID

    """
    return f"urn:uuid:{uuid.uuid4()}"


def generate_edge_identifiers(graph: BaseGraph):
    """
    Generate unique identifiers for edges in a graph that do not
    have an ``id`` field.

    Parameters
    ----------
    graph: kgx.graph.base_graph.BaseGraph

    """
    for u, v, data in graph.edges(data=True):
        if 'biolink:id' not in data:
            data['biolink:id'] = generate_uuid()


def is_curie(s: str) -> bool:
    """
    Check if a given string is a CURIE.

    Parameters
    ----------
    s: str
        A string

    Returns
    -------
    bool
        Whether or not the given string is a CURIE

    """
    if isinstance(s, str):
        m = re.match(r"^[^ <()>:]*:[^/ :]+$", s)
        return bool(m)
    else:
        return False


def is_iri(s: str) -> bool:
    """
    Check if a given string as an IRI.

    Parameters
    ----------
    s: str
        A string

    Returns
    -------
    bool
        Whether or not the given string is an IRI.

    """
    if isinstance(s, str):
        return s.startswith('http') or s.startswith('https')
    else:
        return False


def curiefy(data: Dict, prefix: str = 'biolink'):
    new_data = {}
    toolkit = get_toolkit()

    for k, v in data.items():
        if is_curie(k):
            new_data[k] = v
        else:
            if isa_biolink_property(k):
                prop_curie = f"{prefix}:{k}"
                new_data[prop_curie] = v
            else:
                new_data[k] = v
    return new_data


def isa_biolink_property(p):
    toolkit = get_toolkit()
    node_properties = [x.split(':', 1)[1] for x in toolkit.get_all_node_properties(formatted=True)]
    edge_properties = [x.split(':', 1)[1] for x in toolkit.get_all_edge_properties(formatted=True)]
    predicates = [x.split(':', 1)[1] for x in toolkit.get_descendants('related to', formatted=True)]
    properties = set(node_properties + edge_properties + predicates)
    return p in properties
