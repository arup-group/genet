

def validate_link_data(link_attributes):
    assert 'id' in link_attributes
    assert 'from' in link_attributes
    assert 'to' in link_attributes
    assert 'length' in link_attributes
    assert 'freespeed' in link_attributes
    assert 'capacity' in link_attributes
    assert 'permlanes' in link_attributes
    assert 'oneway' in link_attributes
    assert 'modes' in link_attributes
