import anki.collection
import anki.notes
import rdflib


def fields_as_graph(note: anki.notes.Note) -> rdflib.Graph:
    graph = rdflib.Graph()
    with open('tmp.txt') as f:
        already_evaluated = [line.split(sep=' ')[3][:-1] for line in f.readlines()]
    for label, value in note.items():
        if label == 'DE Singular Nominative' and value in already_evaluated:
            return graph
    for label, value in note.items():
        graph.update(
            f'''
            PREFIX anki: <https://veyndan.com/foo/> 
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            INSERT DATA {{
                [] a anki:field;
                    rdfs:label {rdflib.Literal(label).n3()};
                    rdf:value {rdflib.Literal(value).n3()}.
            }}
            ''',
        )
    return graph


if __name__ == '__main__':
    collection = anki.collection.Collection("/Users/veyndan/Library/Application Support/Anki2/Playground/collection.anki2")
    fields = rdflib.Graph()
    for note_id in collection.find_notes("")[:20]:
        note = collection.get_note(note_id)
        print([value for label, value in note.items() if label == 'DE Singular Nominative'])
        fields += fields_as_graph(note)
    print("Querying…")
    query_result = fields.query(
        '''
        PREFIX anki: <https://veyndan.com/foo/>
        
        PREFIX bd: <http://www.bigdata.com/rdf#>
        PREFIX cc: <http://creativecommons.org/ns#>
        PREFIX dct: <http://purl.org/dc/terms/>
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX hint: <http://www.bigdata.com/queryHints#> 
        PREFIX ontolex: <http://www.w3.org/ns/lemon/ontolex#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX prov: <http://www.w3.org/ns/prov#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <http://schema.org/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        PREFIX p: <http://www.wikidata.org/prop/>
        PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
        PREFIX pqn: <http://www.wikidata.org/prop/qualifier/value-normalized/>
        PREFIX pqv: <http://www.wikidata.org/prop/qualifier/value/>
        PREFIX pr: <http://www.wikidata.org/prop/reference/>
        PREFIX prn: <http://www.wikidata.org/prop/reference/value-normalized/>
        PREFIX prv: <http://www.wikidata.org/prop/reference/value/>
        PREFIX psv: <http://www.wikidata.org/prop/statement/value/>
        PREFIX ps: <http://www.wikidata.org/prop/statement/>
        PREFIX psn: <http://www.wikidata.org/prop/statement/value-normalized/>
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdata: <http://www.wikidata.org/wiki/Special:EntityData/>
        PREFIX wdno: <http://www.wikidata.org/prop/novalue/>
        PREFIX wdref: <http://www.wikidata.org/reference/>
        PREFIX wds: <http://www.wikidata.org/entity/statement/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        PREFIX wdtn: <http://www.wikidata.org/prop/direct-normalized/>
        PREFIX wdv: <http://www.wikidata.org/value/>
        PREFIX wikibase: <http://wikiba.se/ontology#>

        SELECT ?item ?enSingularLexicalEntry ?deSingularNominativeLexicalEntry ?deSingularNominative WHERE {
            [] a anki:field;
                rdfs:label "EN Singular";
                rdf:value ?enSingularUnlocalized.
            [] a anki:field;
                rdfs:label "DE Singular Nominative";
                rdf:value ?deSingularNominativeUnlocalized.

            BIND(STRLANG(?enSingularUnlocalized, "en") AS ?enSingular)
            BIND(STRLANG(?deSingularNominativeUnlocalized, "de") AS ?deSingularNominative)
            SERVICE <https://query.wikidata.org/sparql> {
                OPTIONAL {
                    ?enSingularLexicalEntry ontolex:sense ?enSingularSense;
                        dct:language wd:Q1860;
                        wikibase:lexicalCategory wd:Q1084;
                        wikibase:lemma ?enSingular.
                    ?enSingularSense wdt:P5137 ?item.
                    ?deSingularNominativeLexicalEntry ontolex:sense ?deSingularNominativeSense;
                        dct:language wd:Q188;
                        wikibase:lemma ?deSingularNominative.
                    ?deSingularNominativeSense wdt:P5137 ?item.
                }
            }
            SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        }
        '''
    )
    with open('tmp.txt', 'a') as f:
        f.writelines([binding['item'].n3() + ' ' + binding['enSingularLexicalEntry'].n3() + ' ' + binding['deSingularNominativeLexicalEntry'].n3() + ' ' + binding['deSingularNominative'].value for binding in query_result])
        f.write('\n')
    for foo in query_result:
        print(foo)
    collection.close()
