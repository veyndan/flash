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


def generate_note(editor: aqt.editor.Editor, note: anki.notes.Note) -> anki.notes.Note:
    # noinspection HttpUrlsUsage,SpellCheckingInspection
    query_result = rdflib.Graph().query(
        rdflib.plugins.sparql.prepareQuery(
            textwrap.dedent(
                f'''
                PREFIX anki: <https://veyndan.com/foo/>
                PREFIX bd: <http://www.bigdata.com/rdf#>
                PREFIX dct: <http://purl.org/dc/terms/>
                PREFIX ontolex: <http://www.w3.org/ns/lemon/ontolex#>
                PREFIX p: <http://www.wikidata.org/prop/>
                PREFIX ps: <http://www.wikidata.org/prop/statement/>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX wd: <http://www.wikidata.org/entity/>
                PREFIX wdref: <http://www.wikidata.org/reference/>
                PREFIX wdt: <http://www.wikidata.org/prop/direct/>
                PREFIX wikibase: <http://wikiba.se/ontology#>
                
                CONSTRUCT {{
                    _:enSingularField a anki:field;
                        rdfs:label "EN Singular";
                        rdf:value ?enSingular.
                    
                    _:enPluralField a anki:field;
                        rdfs:label "EN Plural";
                        rdf:value ?enPlural.
                    
                    _:enUsageExampleField a anki:field;
                        rdfs:label "EN Usage Example";
                        rdf:value ?enUsageExample.
                    
                    _:deSingularNominativeField a anki:field;
                        rdfs:label "DE Singular Nominative";
                        rdf:value ?deSingularNominative.
                    
                    _:deSingularNominativeDefiniteArticleRepresentation a anki:field;
                        rdfs:label "DE Singular Nominative Definite Article";
                        rdf:value ?deSingularNominativeDefiniteArticleRepresentation.
                    
                    _:dePronunciationAudioSingularNominativeUrl1 a anki:field;
                        rdfs:label "DE Singular Nominative Pronunciation";
                        rdf:value ?dePronunciationAudioSingularNominativeUrl1.
                    
                    _:dePluralNominative1 a anki:field;
                        rdfs:label "DE Plural Nominative";
                        rdf:value ?dePluralNominative1.
                    
                    _:dePluralNominativeDefiniteArticleRepresentation a anki:field;
                        rdfs:label "DE Plural Nominative Definite Article";
                        rdf:value ?dePluralNominativeDefiniteArticleRepresentation.
                    
                    _:dePronunciationAudioPluralNominativeUrl1 a anki:field;
                        rdfs:label "DE Plural Nominative Pronunciation";
                        rdf:value ?dePronunciationAudioPluralNominativeUrl1.
                }}
                WHERE {{
                    SELECT DISTINCT ?enPlural ?enUsageExample ?deSingularNominativeDefiniteArticleRepresentation (MIN(?dePronunciationAudioSingularNominativeUrl) AS ?dePronunciationAudioSingularNominativeUrl1) (MIN(?dePluralNominative) AS ?dePluralNominative1) ?dePluralNominativeDefiniteArticleRepresentation (MIN(?dePronunciationAudioPluralNominativeUrl) AS ?dePronunciationAudioPluralNominativeUrl1) WHERE {{
                        VALUES ?dePluralNominativeDefiniteArticleRepresentation {{
                            "die"@de
                        }}
                        
                        SERVICE <https://query.wikidata.org/sparql> {{
                            ?enLexicalEntity rdf:type ontolex:LexicalEntry;
                                dct:language wd:Q1860;
                                wikibase:lexicalCategory wd:Q1084;
                                wikibase:lemma ?enSingular;
                                ontolex:lexicalForm ?enLexicalForm.
                            ?enLexicalForm wikibase:grammaticalFeature wd:Q146786;
                                ontolex:representation ?enPlural.
                            OPTIONAL {{ ?enLexicalEntity wdt:P5831 ?enUsageExample. }}
                            MINUS {{ ?enLexicalForm wikibase:grammaticalFeature wd:Q1861696. }}
                            ?deLexicalEntity rdf:type ontolex:LexicalEntry;
                                dct:language wd:Q188;
                                wikibase:lemma ?deSingularNominative;
                                wdt:P5185 ?deSingularNominativeGrammaticalGender;
                                ontolex:lexicalForm ?deLexicalForm.
                            ?deDefiniteArticleLexicalEntity wikibase:lexicalCategory wd:Q2865743;
                                dct:language wd:Q188;
                                ontolex:lexicalForm ?deDefiniteArticleLexicalForm.
                            ?deDefiniteArticleLexicalForm wikibase:grammaticalFeature wd:Q110786, wd:Q131105, ?deSingularNominativeGrammaticalGender;
                                ontolex:representation ?deSingularNominativeDefiniteArticleRepresentation.
                            {{
                                ?deLexicalForm wikibase:grammaticalFeature wd:Q110786, wd:Q131105;
                                    p:P443 ?dePronunciationAudioSingularNominative.
                                ?dePronunciationAudioSingularNominative ps:P443 ?dePronunciationAudioSingularNominativeUrl.
                            }}
                            UNION
                            {{
                                ?deLexicalForm wikibase:grammaticalFeature wd:Q146786, wd:Q131105;
                                    ontolex:representation ?dePluralNominative;
                                p:P443 ?dePronunciationAudioPluralNominative.
                                ?dePronunciationAudioPluralNominative ps:P443 ?dePronunciationAudioPluralNominativeUrl.
                            }}
                        }}
                        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
                    }}
                }}
                '''
            )
        ),
        initBindings={
            'enSingular': rdflib.Literal(note['EN Singular'], lang='en'),
            'deSingularNominative': rdflib.Literal(note['DE Singular Nominative'], lang='de'),
        }
    )

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
