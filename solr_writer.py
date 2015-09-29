__author__ = 'malone'

import pysolr


def write_to_solr(data):
    # Setup a Solr instance. The timeout is optional.
    solr = pysolr.Solr('http://localhost:8983/solr/b2note_index/', timeout=10)

    # How you'd index data.
    solr.add(data)
    print "data added to solr"
