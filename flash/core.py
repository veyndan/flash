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
    g = fields_as_graph(
        [
            ("Item For This Sense", "bread"),
            ("EN Singular", "bread"),
            ("EN Plural", ""),
            ("EN Usage Example", ""),
            # There are two words which has "bread" for an "Item For This Sense".
            # Looking at the "All entered languages" section of https://www.wikidata.org/wiki/Q7802 we find Brot.
            # However, this might be a special case.
            # A more generic thing would be to display a warning dialog saying that there are two options (can just log it to the console for now).
            # Then the user decides which one they want, and copy-paste the word into the correct spot.
            # This is conceptually the better way of doing things for the time being as it's very generic and fits the SPARQL model.

            # I just need to check the following in de_en.rq:
            # - Only one set of results is returned
            # - Item For This Sense is bound OR (EN Singular is bound AND DE Singular Nominative is bound)
            ("DE Singular Nominative", "Brot"),
            ("DE Singular Nominative Definite Article", ""),
            ("DE Singular Nominative Pronunciation", ""),
            ("DE Plural Nominative", ""),
            ("DE Plural Nominative Definite Article", ""),
            ("DE Plural Nominative Pronunciation", ""),
        ],
        True,
    )
    with urllib.request.urlopen("http://localhost:9090/flash/de_en.rq") as response:
        prepared_query = rdflib.plugins.sparql.prepareQuery(response.read())
    query_result = g.query(prepared_query)
    query_result2 = query_result.graph.query(
        """
        PREFIX anki: <https://veyndan.com/foo/>
        
        SELECT * WHERE {
            ?a a anki:field;
                rdfs:label ?fieldLabel.
            OPTIONAL {
                ?a rdf:value ?fieldValue.
            }
        }
        """
    )
    for binding in query_result2:
        label2: rdflib.Literal = binding["fieldLabel"]
        value2: rdflib.Literal = binding["fieldValue"]
        print(f"({label2}, {value2})")
