import pytest

import numpy as np
import pybinding as pb
from pybinding.repository import graphene

lattices = {
    'graphene-monolayer': graphene.monolayer(),
    'graphene-monolayer-alt': graphene.monolayer_alt(),
    'graphene-monolayer-4atom': graphene.monolayer_4atom(),
    'graphene-monolayer-nn': graphene.monolayer(2),
    'graphene-bilayer': graphene.bilayer(),
}


@pytest.fixture(scope='module', ids=list(lattices.keys()), params=lattices.values())
def lattice(request):
    return request.param


@pytest.fixture
def mock_lattice():
    a_cc, a, t = 1, 1.73, 1
    lat = pb.Lattice([a, 0], [0.5 * a, 0.866 * a])
    lat.add_sublattices(
        ['a', (0, -a_cc/2)],
        ['b', (0,  a_cc/2)]
    )
    lat.add_hoppings(
        [(0,  0), 'a', 'b', t],
        [(1, -1), 'a', 'b', t],
        [(0, -1), 'a', 'b', t]
    )
    lat.min_neighbors = 2
    return lat


def test_init():
    lat1d = pb.Lattice(1)
    assert len(lat1d.vectors) == 1
    assert pytest.fuzzy_equal(lat1d.vectors[0], [1, 0, 0])

    lat2d = pb.Lattice([1, 0], [0, 1])
    assert len(lat2d.vectors) == 2
    assert pytest.fuzzy_equal(lat2d.vectors[0], [1, 0, 0])
    assert pytest.fuzzy_equal(lat2d.vectors[1], [0, 1, 0])

    lat3d = pb.Lattice([1, 0, 0], [0, 1, 0], [0, 0, 1])
    assert len(lat3d.vectors) == 3
    assert pytest.fuzzy_equal(lat3d.vectors[0], [1, 0, 0])
    assert pytest.fuzzy_equal(lat3d.vectors[1], [0, 1, 0])
    assert pytest.fuzzy_equal(lat3d.vectors[2], [0, 0, 1])


def test_add_sublattice(mock_lattice):
    with pytest.raises(RuntimeError) as excinfo:
        mock_lattice.add_one_sublattice('', [0, 0])
    assert "Sublattice name can't be blank" in str(excinfo.value)

    with pytest.raises(RuntimeError) as excinfo:
        mock_lattice.add_one_sublattice('a', (0, 0))
    assert "Sublattice 'a' already exists" in str(excinfo.value)

    with pytest.raises(RuntimeError) as excinfo:
        for i in range(127):
            mock_lattice.add_one_sublattice(str(i), (0, 0))
    assert "Exceeded maximum number of unique sublattices" in str(excinfo.value)

    pytest.deprecated_call(mock_lattice.__getitem__, "a")


def test_add_multiorbital_sublattice(mock_lattice):
    mock_lattice.add_one_sublattice("C", [0, 0], [1, 2, 3])
    mock_lattice.add_one_sublattice("D", [0, 0], [[1, 2, 3],
                                                  [0, 4, 5],
                                                  [0, 0, 6]])
    mock_lattice.add_one_sublattice("E", [0, 0], [[1, 2, 3],
                                                  [2, 4, 5],
                                                  [3, 5, 6]])

    with pytest.raises(RuntimeError) as excinfo:
        mock_lattice.add_one_sublattice("zero-dimensional", [0, 0], [])
    assert "can't be zero-dimensional" in str(excinfo.value)

    with pytest.raises(RuntimeError) as excinfo:
        mock_lattice.add_one_sublattice("complex onsite energy", [0, 0], [1j, 2j, 3j])
    assert "must be a real vector or a square matrix" in str(excinfo.value)

    with pytest.raises(RuntimeError) as excinfo:
        mock_lattice.add_one_sublattice("not square", [0, 0], [[1, 2, 3],
                                                               [4, 5, 6]])
    assert "must be a real vector or a square matrix" in str(excinfo.value)

    with pytest.raises(RuntimeError) as excinfo:
        mock_lattice.add_one_sublattice("not square", [0, 0], [[1j, 2,  3],
                                                               [2,  4j, 5],
                                                               [3,  5,  6j]])
    assert "The main diagonal of the onsite hopping term must be real" in str(excinfo.value)

    with pytest.raises(RuntimeError) as excinfo:
        mock_lattice.add_one_sublattice("not Hermitian", [0, 0], [[1, 2, 3],
                                                                  [4, 5, 6],
                                                                  [7, 8, 9]])
    assert "The onsite hopping matrix must be upper triangular or Hermitian" in str(excinfo.value)


def test_add_sublattice_alias(mock_lattice):
    c_position = [0, 9]
    mock_lattice.add_one_alias("c", "a", c_position)
    model = pb.Model(mock_lattice)
    c_index = model.system.find_nearest(c_position)

    assert mock_lattice.sub_name_to_id["c"] != mock_lattice.sub_name_to_id["a"]
    assert model.system.sublattices[c_index] == mock_lattice.sub_name_to_id["a"]
    assert c_index in np.argwhere(model.system.sublattices == "a")

    with pytest.raises(IndexError) as excinfo:
        mock_lattice.add_one_alias('d', 'bad_name', [0, 0])
    assert "There is no sublattice named 'bad_name'" in str(excinfo.value)

    pytest.deprecated_call(mock_lattice.add_one_sublattice, "z", c_position, alias="a")


def test_add_hopping(mock_lattice):
    with pytest.raises(RuntimeError) as excinfo:
        mock_lattice.add_one_hopping((0,  0), 'a', 'b', 1)
    assert "hopping already exists" in str(excinfo.value)

    with pytest.raises(RuntimeError) as excinfo:
        mock_lattice.add_one_hopping((0, 0), 'a', 'a', 1)
    assert "Don't define onsite energy here" in str(excinfo.value)

    with pytest.raises(IndexError) as excinfo:
        mock_lattice.add_one_hopping((0, 0), 'c', 'a', 1)
    assert "There is no sublattice named 'c'" in str(excinfo.value)

    mock_lattice.register_hopping_energies({
        't_nn': 0.1,
        't_nnn': 0.01
    })
    assert "t_nn" in mock_lattice.hop_name_to_id
    assert "t_nnn" in mock_lattice.hop_name_to_id

    mock_lattice.add_one_hopping((0, 1), 'a', 'a', 't_nn')

    with pytest.raises(RuntimeError) as excinfo:
        mock_lattice.register_hopping_energies({'': 0.0})
    assert "Hopping name can't be blank" in str(excinfo.value)

    with pytest.raises(RuntimeError) as excinfo:
        mock_lattice.register_hopping_energies({'t_nn': 0.2})
    assert "Hopping 't_nn' already exists" in str(excinfo.value)

    with pytest.raises(IndexError) as excinfo:
        mock_lattice.add_one_hopping((0, 1), 'a', 'a', 'tt')
    assert "There is no hopping named 'tt'" in str(excinfo.value)

    with pytest.raises(RuntimeError) as excinfo:
        for i in range(1, 128):
            mock_lattice.add_one_hopping((0, i), 'a', 'b', i)
    assert "Exceeded maximum number of unique hoppings energies" in str(excinfo.value)

    pytest.deprecated_call(mock_lattice.__call__, "t_nn")


def test_add_matrix_hopping(mock_lattice):
    mock_lattice.add_sublattices(
        ("A2", [0, 0], [1, 2]),
        ("B2", [0, 0], [1, 2]),
        ("C3", [0, 0], [1, 2, 3]),
    )

    mock_lattice.register_hopping_energies({
        "t22": [[1, 2],
                [3, 4]],
        "t23": [[1, 2, 3],
                [4, 5, 6]],
    })

    with pytest.raises(RuntimeError) as excinfo:
        mock_lattice.register_hopping_energies({"zero-dimensional": []})
    assert "can't be zero-dimensional" in str(excinfo.value)

    mock_lattice.add_hoppings(
        ([0, 0], "A2", "B2", "t22"),
        ([1, 0], "A2", "A2", "t22"),
        ([0, 0], "A2", "C3", "t23"),
        ([1, 0], "A2", "C3", "t23"),
    )

    with pytest.raises(RuntimeError) as excinfo:
        mock_lattice.add_one_hopping([0, 0], 'A2', 'A2', "t22")
    assert "Don't define onsite energy here" in str(excinfo.value)

    with pytest.raises(RuntimeError) as excinfo:
        mock_lattice.add_one_hopping([0, 0], 'B2', 'C3', "t22")
    assert "size mismatch: from 'B2' (2) to 'C3' (3) with matrix 't22' (2, 2)" in str(excinfo.value)

    with pytest.raises(RuntimeError) as excinfo:
        mock_lattice.add_one_hopping([0, 0], 'C3', 'B2', "t23")
    assert "size mismatch: from 'C3' (3) to 'B2' (2) with matrix 't23' (2, 3)" in str(excinfo.value)


def test_builder():
    """Builder pattern methods"""
    lattice = pb.Lattice([1, 0], [0, 1])

    copy = lattice.with_offset([0, 0.5])
    assert pytest.fuzzy_equal(copy.offset, [0, 0.5, 0])
    assert pytest.fuzzy_equal(lattice.offset, [0, 0, 0])

    copy = lattice.with_min_neighbors(5)
    assert copy.min_neighbors == 5
    assert lattice.min_neighbors == 1


def test_pickle_round_trip(lattice, tmpdir):
    file_name = str(tmpdir.join('file.npz'))
    pb.save(lattice, file_name)
    from_file = pb.load(file_name)

    assert pytest.fuzzy_equal(lattice, from_file)


@pytest.mark.skip(reason="TODO: revise Lattice before committing to a new binary format")
def test_expected(lattice, baseline, plot_if_fails):
    expected = baseline(lattice)
    plot_if_fails(lattice, expected, 'plot')

    assert pytest.fuzzy_equal(lattice, expected)


def test_brillouin_zone():
    from math import pi, sqrt

    lat = pb.Lattice(a1=1)
    assert pytest.fuzzy_equal(lat.brillouin_zone(), [-pi, pi])

    lat = pb.Lattice(a1=[0, 1], a2=[0.5, 0.5])
    assert pytest.fuzzy_equal(lat.brillouin_zone(),
                              [[0, -2 * pi], [2 * pi, 0], [0, 2 * pi], [-2 * pi, 0]])

    # Identical lattices represented using acute and obtuse angles between primitive vectors
    acute = pb.Lattice(a1=[1, 0], a2=[1/2, 1/2 * sqrt(3)])
    obtuse = pb.Lattice(a1=[1/2, 1/2 * sqrt(3)], a2=[1/2, -1/2 * sqrt(3)])
    assert pytest.fuzzy_equal(acute.brillouin_zone(), obtuse.brillouin_zone())
