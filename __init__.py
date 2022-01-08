import sys
import textwrap
import typing

import anki.hooks
import anki.notes
import aqt.deckbrowser
import aqt.editor
import aqt.operations
import aqt.operations.note
import aqt.utils
import aqt.webview

sys.path.append('/Users/veyndan/IdeaProjects/myankiplugin/stdlib')  # Required until 3.1.50 is released
sys.path.append('/Users/veyndan/IdeaProjects/myankiplugin/.venv/lib/python3.9/site-packages')

import rdflib  # noqa: E402
import rdflib.plugins.sparql  # noqa: E402
import rdflib.plugins.sparql.sparql  # noqa: E402

fields_state_initial = rdflib.Graph().parse(
    data=textwrap.dedent(
        f'''
        PREFIX anki: <https://veyndan.com/foo/>
        PREFIX dct: <http://purl.org/dc/terms/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        anki:enSingular a anki:field;
            rdfs:label "EN Singular";
            dct:language "en";
            anki:regex ".*";
            anki:required true.
        
        anki:enPluralField a anki:field;
            rdfs:label "EN Plural";
            dct:language "en";
            anki:required false.
        
        anki:enUsageExampleField a anki:field;
            rdfs:label "EN Usage Example";
            dct:language "en";
            anki:required false.
        
        anki:deSingularNominativeField a anki:field;
            rdfs:label "DE Singular Nominative";
            dct:language "de";
            anki:required true.
        
        anki:deSingularNominativeDefiniteArticleRepresentation a anki:field;
            rdfs:label "DE Singular Nominative Definite Article";
            dct:language "de";
            anki:allowedValue "der", "die", "das";
            anki:required false.
        
        anki:dePronunciationAudioSingularNominativeUrl1 a anki:field;
            rdfs:label "DE Singular Nominative Pronunciation";
            anki:required false.
        
        anki:dePluralNominative1 a anki:field;
            rdfs:label "DE Plural Nominative";
            dct:language "de";
            anki:required false.
        
        anki:dePluralNominativeDefiniteArticleRepresentation a anki:field;
            rdfs:label "DE Plural Nominative Definite Article";
            dct:language "de";
            anki:required false.
        
        anki:dePronunciationAudioPluralNominativeUrl1 a anki:field;
            rdfs:label "DE Plural Nominative Pronunciation";
            anki:required false.
        '''
    )
)


def generate_note(editor: aqt.editor.Editor, note: anki.notes.Note) -> anki.notes.Note:
    prepared_query_field_required_language_tag = rdflib.plugins.sparql.prepareQuery(
        textwrap.dedent(
            f'''
            PREFIX anki: <https://veyndan.com/foo/>
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
            SELECT ?field ?fieldLabel ?fieldLanguageTag WHERE {{
                ?field a anki:field;
                    rdfs:label ?fieldLabel;
                    dct:language ?fieldLanguageTag;
                    anki:required true.
            }}
            '''
        )
    )

    fields_state_initial_with_required = rdflib.Graph()
    fields_state_initial_with_required += fields_state_initial

    # This is only necessary due to the limitation (in my knowledge of RDF or RDF itself) that we can't dynamically
    #  specify the language tag, e.g., as a separate RDF triple (https://www.w3.org/wiki/Languages_as_RDF_Resources).
    for binding in fields_state_initial.query(prepared_query_field_required_language_tag):
        field: rdflib.URIRef = binding['field']
        field_label: rdflib.Literal = binding['fieldLabel']
        fields_state_initial_with_required += rdflib.Graph() \
            .add((field, rdflib.RDF.type, rdflib.URIRef('https://veyndan.com/foo/field'))) \
            .add((field, rdflib.RDFS.label, field_label)) \
            .add((field, rdflib.RDF.value, rdflib.Literal(note[field_label.value], lang=binding['fieldLanguageTag'].value)))

    # noinspection HttpUrlsUsage,SpellCheckingInspection
    prepared_query = rdflib.plugins.sparql.prepareQuery(
        textwrap.dedent(
            f'''
            PREFIX anki: <https://veyndan.com/foo/>
            PREFIX bd: <http://www.bigdata.com/rdf#>
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX hint: <http://www.bigdata.com/queryHints#>
            PREFIX ontolex: <http://www.w3.org/ns/lemon/ontolex#>
            PREFIX p: <http://www.wikidata.org/prop/>
            PREFIX ps: <http://www.wikidata.org/prop/statement/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX wd: <http://www.wikidata.org/entity/>
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>
            PREFIX wikibase: <http://wikiba.se/ontology#>

            CONSTRUCT {{
                anki:enSingularField a anki:field;
                    rdfs:label "EN Singular";
                    rdf:value ?enSingular.

                anki:enPluralField a anki:field;
                    rdfs:label "EN Plural";
                    rdf:value ?enPlural.

                anki:enUsageExampleField a anki:field;
                    rdfs:label "EN Usage Example";
                    rdf:value ?enUsageExample.

                anki:deSingularNominativeField a anki:field;
                    rdfs:label "DE Singular Nominative";
                    rdf:value ?deSingularNominative.

                anki:deSingularNominativeDefiniteArticleRepresentation a anki:field;
                    rdfs:label "DE Singular Nominative Definite Article";
                    rdf:value ?deSingularNominativeDefiniteArticleRepresentation.

                anki:dePronunciationAudioSingularNominativeUrl1 a anki:field;
                    rdfs:label "DE Singular Nominative Pronunciation";
                    rdf:value ?dePronunciationAudioSingularNominativeUrl1.

                anki:dePluralNominative1 a anki:field;
                    rdfs:label "DE Plural Nominative";
                    rdf:value ?dePluralNominative1.
                
                anki:dePluralNominativeDefiniteArticleRepresentation a anki:field;
                    rdfs:label "DE Plural Nominative Definite Article";
                    rdf:value "die".
                
                anki:dePronunciationAudioPluralNominativeUrl1 a anki:field;
                    rdfs:label "DE Plural Nominative Pronunciation";
                    rdf:value ?dePronunciationAudioPluralNominativeUrl1.
            }}
            WHERE {{
                SELECT DISTINCT ?enPlural ?enUsageExample ?deSingularNominativeDefiniteArticleRepresentation (MIN(?dePronunciationAudioSingularNominativeUrl) AS ?dePronunciationAudioSingularNominativeUrl1) (MIN(?dePluralNominative) AS ?dePluralNominative1) (MIN(?dePronunciationAudioPluralNominativeUrl) AS ?dePronunciationAudioPluralNominativeUrl1) WHERE {{
                    ?enSingularField a anki:field;
                        rdfs:label "EN Singular";
                        rdf:value ?enSingular.
   
                    ?deSingularNominativeField a anki:field;
                        rdfs:label "DE Singular Nominative";
                        rdf:value ?deSingularNominative.
                    
                    SERVICE <https://query.wikidata.org/sparql> {{
                        hint:Query hint:optimizer "None" .

                        ?deSingularNominativeLexicalEntry wikibase:lemma ?deSingularNominative.
                        ?deSingularNominativeLexicalEntry dct:language wd:Q188.
                        ?deSingularNominativeLexicalEntry wdt:P5185 ?deSingularNominativeGrammaticalGender.
                        ?deSingularNominativeLexicalEntry rdf:type ontolex:LexicalEntry.
                        ?deSingularNominativeLexicalEntry ontolex:lexicalForm ?deSingularNominativeLexicalForm.
                        
                        {{
                            ?deSingularNominativeLexicalForm p:P443 ?dePronunciationAudioSingularNominative.
                            ?dePronunciationAudioSingularNominative ps:P443 ?dePronunciationAudioSingularNominativeUrl.
                            ?deSingularNominativeLexicalForm wikibase:grammaticalFeature wd:Q131105.
                            ?deSingularNominativeLexicalForm wikibase:grammaticalFeature wd:Q110786.
                        }}
                        UNION
                        {{
                            ?deSingularNominativeLexicalForm p:P443 ?dePronunciationAudioPluralNominative.
                            ?dePronunciationAudioPluralNominative ps:P443 ?dePronunciationAudioPluralNominativeUrl.
                            ?deSingularNominativeLexicalForm wikibase:grammaticalFeature wd:Q131105.
                            ?deSingularNominativeLexicalForm wikibase:grammaticalFeature wd:Q146786.
                            ?deSingularNominativeLexicalForm ontolex:representation ?dePluralNominative.
                        }}
                        
                        ?enSingularLexicalEntry wikibase:lemma ?enSingular.
                        ?enSingularLexicalEntry dct:language wd:Q1860.
                        ?enSingularLexicalEntry wikibase:lexicalCategory wd:Q1084.
                        ?enSingularLexicalEntry rdf:type ontolex:LexicalEntry.
                        ?enSingularLexicalEntry ontolex:lexicalForm ?enLexicalForm.
                        
                        ?enLexicalForm wikibase:grammaticalFeature wd:Q146786.
                        ?enLexicalForm ontolex:representation ?enPlural.
                        
                        ?deSingularNominativeDefiniteArticleLexicalEntry wikibase:lexicalCategory wd:Q2865743.
                        ?deSingularNominativeDefiniteArticleLexicalEntry dct:language wd:Q188.
                        ?deSingularNominativeDefiniteArticleLexicalEntry rdf:type ontolex:LexicalEntry.
                        ?deSingularNominativeDefiniteArticleLexicalEntry ontolex:lexicalForm ?deSingularNominativeDefiniteArticleLexicalForm.
                        
                        ?deSingularNominativeDefiniteArticleLexicalForm wikibase:grammaticalFeature ?deSingularNominativeGrammaticalGender.
                        ?deSingularNominativeDefiniteArticleLexicalForm wikibase:grammaticalFeature wd:Q131105.
                        ?deSingularNominativeDefiniteArticleLexicalForm wikibase:grammaticalFeature wd:Q110786.
                        ?deSingularNominativeDefiniteArticleLexicalForm rdf:type ontolex:Form.
                        ?deSingularNominativeDefiniteArticleLexicalForm ontolex:representation ?deSingularNominativeDefiniteArticleRepresentation.
                        
                        OPTIONAL {{ ?enSingularLexicalEntry wdt:P5831 ?enUsageExample. }}
                        MINUS {{ ?enLexicalForm wikibase:grammaticalFeature wd:Q1861696. }}
                    }}
                }}
            }}
            '''
        )
    )

    query_result = fields_state_initial_with_required.query(prepared_query)

    query_result2 = query_result.graph.query(
        rdflib.plugins.sparql.prepareQuery(
            textwrap.dedent(
                f'''
                PREFIX anki: <https://veyndan.com/foo/>
                
                SELECT ?fieldLabel ?fieldValue WHERE {{
                    [] a anki:field;
                        rdfs:label ?fieldLabel;
                        rdf:value ?fieldValue.
                }}
                '''
            )
        )
    )

    for binding in query_result2:
        label: rdflib.Literal = binding['fieldLabel']
        value: rdflib.Literal = binding['fieldValue']
        print(f"({label}, {value})")
        link = editor.urlToLink(value.value)
        note[label.value] = value.value if link is None else link

    return note


def on_generate_clicked(editor: aqt.editor.Editor):
    note = editor.note
    if note is None:
        aqt.utils.showInfo("No note found.")
        return
    actual_note: anki.notes.Note = note

    query_op = aqt.operations.QueryOp(
        parent=editor.mw,
        op=lambda col: generate_note(editor, actual_note),
        success=editor.set_note,
    )

    # QueryOp.with_progress() was broken until Anki 2.1.50 (https://github.com/ankitects/addon-docs/search?q=2.1.50)
    query_op.with_progress().run_in_background()


def add_generate_button(buttons: typing.List[str], editor: aqt.editor.Editor) -> None:
    button = editor.addButton(icon=None, cmd="Generate", func=on_generate_clicked)
    buttons.append(button)


aqt.gui_hooks.editor_did_init_buttons.append(add_generate_button)
