"""
Unspecific client stuff. Not related to Anki. Can map to an Anki plugin, interacting via terminal, or being the backbone of a brand-new flashcard app!
"""

import urllib.request

import rdflib.plugins.sparql


def fields_as_graph(
    fields: list[tuple[str, str]],
    on_generate_clicked: bool,
) -> rdflib.Graph:
    import uuid

    # Replace with BNode once https://github.com/RDFLib/rdflib/pull/2084 is released.
    graph = rdflib.Graph()
    graph.update(
        f"""
        PREFIX anki: <https://veyndan.com/foo/> 
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        INSERT DATA {{
            anki:onGenerateClicked rdf:value {rdflib.Literal(on_generate_clicked).n3()}.
        }}
        """
    )
    for label, value in fields:
        graph.update(
            f"""
            PREFIX anki: <https://veyndan.com/foo/> 
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            INSERT DATA {{
                {(rdflib.URIRef('https://veyndan.com/foo/' + uuid.uuid4().hex)).n3()} a anki:field;
                    rdfs:label {rdflib.Literal(label).n3()};
                    rdf:value {rdflib.Literal(value).n3()}.
            }}
            """,
        )
    return graph


if __name__ == '__main__':
    query_result = rdflib.Graph().query(
        """
        PREFIX wd: <http://www.wikidata.org/entity/>
        
        SELECT * WHERE {
            {
                SELECT ?person ?predicate ?object WHERE {
                    BIND(wd:Q42 AS ?person)
        
                    SERVICE <https://query.wikidata.org/sparql> {
                        ?person ?predicate ?object.
                    }
                }
            }
        
            # TODO Deleting this empty service below makes the service in the subquery get passed the ?person VALUE.
            #  File this bug.
        }
        """
    )
    for binding in query_result:
        print(binding)
