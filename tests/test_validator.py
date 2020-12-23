import os

from kgx import JsonTransformer
from kgx import Validator
from kgx.graph.nx_graph import NxGraph

cwd = os.path.abspath(os.path.dirname(__file__))
resource_dir = os.path.join(cwd, 'resources')
target_dir = os.path.join(cwd, 'target')


def test_validator_bad():
    """
    A fake test to establish a fail condition for validation
    """
    G = NxGraph()
    G.add_node('x', foo=3)
    G.add_node('ZZZ:3', **{'nosuch': 1})
    G.add_edge('x', 'y', **{'baz': 6})
    validator = Validator(verbose=True)
    e = validator.validate(G)
    assert len(e) > 0


def test_validator_good():
    """
    A fake test to establish a success condition for validation
    """
    G = NxGraph()
    G.add_node('UniProtKB:P123456', **{'biolink:id': 'UniProtKB:P123456', 'biolink:name': 'fake', 'biolink:category': ['Biolink:Protein']})
    G.add_node('UBERON:0000001', **{'biolink:id': 'UBERON:0000001', 'biolink:name': 'fake', 'biolink:category': ['Biolink:NamedThing']})
    G.add_node('UBERON:0000002', **{'biolink:id': 'UBERON:0000002', 'biolink:name': 'fake', 'biolink:category': ['Biolink:NamedThing']})
    G.add_edge('UBERON:0000001', 'UBERON:0000002', **{'biolink:id': 'UBERON:0000001-part_of-UBERON:0000002', 'biolink:relation': 'RO:1', 'biolink:predicate': 'biolink:part_of', 'biolink:subject': 'UBERON:0000001', 'biolink:object': 'UBERON:0000002', 'biolink:category': ['biolink:Association']})
    validator = Validator(verbose=True)
    e = validator.validate(G)
    print(validator.report(e))

    assert len(e) == 0


def test_validate_json():
    """
    Validate against a valid representative Biolink Model compliant JSON
    """
    json_file = os.path.join(resource_dir, 'valid.json')
    jt = JsonTransformer()
    jt.parse(json_file)
    validator = Validator()
    e = validator.validate(jt.graph)
    assert len(e) == 0
