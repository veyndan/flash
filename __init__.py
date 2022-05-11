import urllib.request
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

sys.path.append('/Users/veyndan/Development/myankiplugin/.venv/lib/python3.9/site-packages')

import rdflib  # noqa: E402
import rdflib.plugins.sparql  # noqa: E402
import rdflib.plugins.sparql.sparql  # noqa: E402

config = aqt.mw.addonManager.getConfig(__name__)

with urllib.request.urlopen(str(config['url'])) as response:
    fields_state_initial = rdflib.Graph().parse(data=response.read())


def requirement_hints(editor: aqt.editor.Editor) -> None:
    """
    Add hints to the GUI to get the initial state of the note into a form (fields_state_initial) that can be parsed by
    myankiplugin.
    """
    prepared_query_field_required = rdflib.plugins.sparql.prepareQuery(
        textwrap.dedent(
            '''
            PREFIX anki: <https://veyndan.com/foo/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
            SELECT ?fieldLabel WHERE {
                [] a anki:field;
                    anki:required true;
                    rdfs:label ?fieldLabel.
            }
            '''
        )
    )

    for label in [binding['fieldLabel'] for binding in fields_state_initial.query(prepared_query_field_required)]:
        label_value: str = label.value

        editor.web.page().runJavaScript(
            textwrap.dedent(
                f"""
                [...document.querySelectorAll('.label-name')]
                    .filter(field_name => field_name.innerHTML === '{label_value}')
                    .forEach(field_name => field_name.insertAdjacentText('afterend', ' [Required]'));
                """
            )
        )


aqt.gui_hooks.editor_did_load_note.append(requirement_hints)


def generate_note(editor: aqt.editor.Editor, note: anki.notes.Note) -> anki.notes.Note:
    prepared_query_field_required_language_tag = rdflib.plugins.sparql.prepareQuery(
        textwrap.dedent(
            '''
            PREFIX anki: <https://veyndan.com/foo/>
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
            SELECT ?field ?fieldLabel ?fieldLanguageTag WHERE {
                ?field a anki:field;
                    rdfs:label ?fieldLabel;
                    dct:language ?fieldLanguageTag;
                    anki:required true.
            }
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

    prepared_query_query_location = rdflib.plugins.sparql.prepareQuery(
        textwrap.dedent(
            '''
            PREFIX anki: <https://veyndan.com/foo/>
    
            SELECT ?queryLocation WHERE {
                anki:foo anki:bar ?queryLocation.
            }
            '''
        )
    )

    for binding in fields_state_initial.query(prepared_query_query_location):
        query_location: rdflib.URIRef = binding['queryLocation']

    # noinspection HttpUrlsUsage,SpellCheckingInspection
    with urllib.request.urlopen(query_location) as response:
        prepared_query = rdflib.plugins.sparql.prepareQuery(response.read())

    query_result = fields_state_initial_with_required.query(prepared_query)

    query_result2 = query_result.graph.query(
        rdflib.plugins.sparql.prepareQuery(
            textwrap.dedent(
                '''
                PREFIX anki: <https://veyndan.com/foo/>
                
                SELECT ?fieldLabel ?fieldValue WHERE {
                    [] a anki:field;
                        rdfs:label ?fieldLabel;
                        rdf:value ?fieldValue.
                }
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

    query_op.with_progress().run_in_background()


def add_generate_button(buttons: typing.List[str], editor: aqt.editor.Editor) -> None:
    button = editor.addButton(icon=None, cmd="Generate", func=on_generate_clicked)
    buttons.append(button)


aqt.gui_hooks.editor_did_init_buttons.append(add_generate_button)
