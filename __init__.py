import sys
import textwrap
import typing

import anki.hooks
import anki.notes
import aqt.deckbrowser
import aqt.editor
import aqt.operations
import re
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
                GROUP BY ?enPlural ?enUsageExample ?deSingularNominativeDefiniteArticleRepresentation ?dePluralNominativeDefiniteArticleRepresentation
                '''
            )
        ),
        initBindings={
            'enSingular': rdflib.Literal(note['EN Singular (enSingular)'], lang='en'),
            'deSingularNominative': rdflib.Literal(note['DE Singular Nominative (deSingularNominative)'], lang='de'),
        }
    )

    assert len(query_result.bindings) == 1, f"Expected 1 binding but received {len(query_result.bindings)} bindings"

    binding: rdflib.plugins.sparql.sparql.FrozenBindings = query_result.bindings[0]

    class BindingNameToFieldName(typing.NamedTuple):
        binding_name: str
        field_name: str

    binding_name_to_field_names = []
    for key in note.keys():
        match = re.search(r"^.+ \((.+)\)$", key)
        if match is not None:
            binding_name_to_field_names.append(BindingNameToFieldName(match[1], key))
        else:
            print(f"No matches for {key}")

    for binding_name_to_field_name in binding_name_to_field_names:
        field_literal_value: typing.Optional[rdflib.term.Literal] = binding[rdflib.term.Variable(binding_name_to_field_name.binding_name)]
        if field_literal_value is not None:
            field_link_value = editor.urlToLink(field_literal_value)
            note[binding_name_to_field_name.field_name] = field_literal_value if field_link_value is None else field_link_value

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
