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


def requirement_hints(editor: aqt.editor.Editor) -> None:
    """
    Add hints to the GUI to get the initial state of the note into a form (fields_state_initial) that can be parsed by
    myankiplugin.
    """
    note = editor.note
    if note is None:
        aqt.utils.showInfo("No note found.")
        return
    actual_note: anki.notes.Note = note

    fields_state_initial = rdflib.Graph()
    with urllib.request.urlopen(next(query for query in config['urls'] if query['noteTypeId'] == actual_note.mid)['url']) as response:
        prepared_query = rdflib.plugins.sparql.prepareQuery(response.read())

    query_result = fields_state_initial.query(prepared_query)

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

    for label in [binding['fieldLabel'] for binding in query_result.graph.query(prepared_query_field_required)]:
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
    fields_state_initial = rdflib.Graph()
    for (label, value) in note.items():
        import uuid
        field_subject = rdflib.URIRef('https://veyndan.com/foo/' + uuid.uuid4().hex)  # TODO For some reason I can't use blank node
        fields_state_initial \
            .add((field_subject, rdflib.RDF.type, rdflib.URIRef('https://veyndan.com/foo/field'))) \
            .add((field_subject, rdflib.RDFS.label, rdflib.Literal(label))) \
            .add((field_subject, rdflib.RDF.value, rdflib.Literal(value)))

    with urllib.request.urlopen(next(query for query in config['urls'] if query['noteTypeId'] == note.mid)['url']) as response:
        prepared_query = rdflib.plugins.sparql.prepareQuery(response.read())

    query_result = fields_state_initial.query(prepared_query)

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
