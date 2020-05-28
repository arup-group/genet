from genet.schedule_elements import Service
from tests.fixtures import *


def test_services_equal():
    a = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    b = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    assert a == b


def test_services_exact():
    a = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    b = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    assert a.is_exact(b)


def test_route_isin_exact_list(test_service):
    a = test_service

    assert a.isin_exact([test_service, test_service])


def test_route_is_not_in_exact_list(similar_non_exact_test_route, test_service):
    a = Service(id='service',
                routes=[similar_non_exact_test_route])

    assert not a.isin_exact([test_service, test_service])