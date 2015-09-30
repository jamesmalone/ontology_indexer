import datetime
from ontospy import ontospy
import itertools
import json
import sys
import rdflib
from solr_writer import write_to_solr

__author__ = 'malone'

class JSONOntology():
    def __init__(self):
        self.class_in_json = []

    def print_all(self):
        for doc in self.class_in_json:
            print doc


class OntologyClass(object):

    def __init__(self):
        self.labels = []
        self.synonyms = []
        self.direct_parents = []
        self.ancestors = []
        self.direct_children = []
        self.descendants = []
        self.uris = []
        self.description = []
        self.indexed_date = ""
        self.text_auto = "empty"

    def print_self(self):
        print "for class: %s" %self.uris
        print "direct parents: %s" %self.direct_parents
        print "ancestors are (%d) %s" %(len(self.ancestors), self.ancestors)
        print "direct subclass: %s" %self.direct_children
        print "descendants are (%d) %s" %(len(self.descendants), self.descendants)
        print "indexed date: %s" %self.indexed_date
        print ""

    def set_uris(self, uris):
        if isinstance(uris, list):
            for o in uris:
                temp_uri = o.uri
                self.uris.append(temp_uri.toPython())
        else:
            self.uris.append(uris.uri.toPython())


    def set_direct_parents(self, direct_parents):
        for o in direct_parents:
            temp_uri = o.uri
            self.direct_parents.append(temp_uri.toPython())

    def set_descendants(self, descendants):
        for o in descendants:
            temp_uri = o.uri
            self.descendants.append(temp_uri.toPython())

    def set_direct_children(self, children):
        for o in children:
            temp_uri = o.uri
            self.direct_children.append(temp_uri.toPython())

    def set_ancestors(self, ancestors):
        for o in ancestors:
            temp_uri = o.uri
            self.ancestors.append(temp_uri.toPython())

    def set_synonyms(self, synonyms):
        for a in synonyms:
            self.synonyms.append(a.value)

    def set_label(self, labels):
        for a in labels:
            self.labels.append(a.value)

    def create_text_auto_from_labels(self):
        #merge labels
        if self.labels:
            self.text_auto = ' '.join(self.labels)

    def to_JSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
            sort_keysv=True, indent=4)

#encode the object as python json object
class MyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if not isinstance(obj, OntologyClass):
            return super(MyJSONEncoder, self).default(obj)
        return obj.__dict__



class OntologyManager():

    def __init__(self):
        #annotation property IRIs which are required to be indexed
        self.synonym_uri = ""
        #primary rendering label - default is rdfs:label
        self.primary_label_uri = "http://www.w3.org/2000/01/rdf-schema#label"

    #load the ontology into the manager
    def load_ontology(self, ontology_location):
        graph = ontospy.Graph(ontology_location)
        return graph

    def get_class_axioms(self, entity):

        #get all descendants to leaf node
        all_descendants = entity.descendants()

        #get direct descendant
        direct_children = entity.children()

        #get direct parents
        direct_parents = entity.parents()

        #get all ancestors to root
        all_ancestors = entity.ancestors()
        return all_descendants, direct_children, all_ancestors, direct_parents

    def get_annotations(self, entity, annotation_uri):
        property = rdflib.URIRef(annotation_uri)
        annotations = entity.getValuesForProperty(property)
        return annotations

    #add all data to dictionary
    def add_all_to_dictionary(self, graph):

        #container for all ontology classes
        container = []
        classes_analysed = set()

        #get top level classes
        top_layer = graph.toplayer

        #get each top class in the ontology
        for top_entity in top_layer:
            classes_analysed.add(top_entity)

            #get all children for each class in turn
            children = top_entity.children()

            all_descendants, direct_children, all_ancestors, direct_parents  = self.get_class_axioms(top_entity)
            print "for TOP class: %s" %top_entity.uri
            print "direct parents: %s" %direct_parents
            print "ancestors are (%d) %s" %(len(all_ancestors), all_ancestors)
            print "direct subclass: %s" %direct_children
            print "descendants are (%d) %s" %(len(all_descendants), all_descendants)
            print ""

            #while the list is not empty
            while children:
                next_children = []
                #repeat with each descendant
                for entity in children:
                    if entity not in classes_analysed:
                        classes_analysed.add(entity)

                        #get all class metadata
                        all_descendants, direct_children, all_ancestors, direct_parents = self.get_class_axioms(entity)

                        #write to obejct for serialising to json
                        ontology_class = OntologyClass()
                        ontology_class.set_uris(entity)
                        ontology_class.set_descendants(all_descendants)
                        ontology_class.set_ancestors(all_ancestors)
                        ontology_class.set_direct_children(direct_children)
                        ontology_class.set_direct_parents(direct_parents)

                        #add annotations
                        synonyms = self.get_annotations(entity, self.synonym_uri)
                        ontology_class.set_synonyms(synonyms)
                        labels = self.get_annotations(entity, self.primary_label_uri)
                        ontology_class.set_label(labels)

                        #form autocomplete field
                        #you can form this in solr but probably to do it here to control it
                        #example below merges all labels but you could also use synonyms
                        ontology_class.create_text_auto_from_labels()


                        #set datetime
                        date_now = datetime.datetime.today().strftime("%Y-%m-%dT00:00:00Z")
                        ontology_class.indexed_date = date_now

                        #add to container
                        container.append(ontology_class.__dict__)

                        next_children.append(direct_children)
                    else:
                        print '**skipping** %s already in list' %entity

                #merge all gathered descendants at this level to one list
                children = list(itertools.chain(*next_children))
        return container


# execute if class called to run
#below is a basic worflow to create the dictionary
# required to populate the solr index using pysolr
if __name__ == '__main__':

    if sys.argv[1:]:
        #if main method called get the ontology as parameter
        ontology_location = sys.argv[1:]
        print "Starting ontology population script..."

        #new ontology manager class
        manager = OntologyManager()
        #set uri properties for annotations you want to include such as synonym and label
        manager.synonym_uri = "http://www.vehicles/synonym"

        location = ontology_location[0]

        graph = manager.load_ontology(location)
        #or load locally if parameter has not been passed using:
        #graph = load_ontology('/Users/seppblatter/Desktop/fifa_expenses.owl')
        print "Ontology loading complete"
        #create the dictionary and store in a container
        # which is a list of OntologyClass objects
        container = manager.add_all_to_dictionary(graph=graph)
        #write this to solr using the solr_writer python script
        write_to_solr(container)
    else:
        print "no ontology to load - please specify a file or URL as ontology location"


