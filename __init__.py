import sys
import textwrap
import typing
import urllib.request

import anki.hooks
import anki.notes
import anki.stdmodels
import aqt.deckbrowser
import aqt.editor
import aqt.models
import aqt.operations
import aqt.operations.note
import aqt.operations.notetype
import aqt.qt
import aqt.utils
import aqt.utils
import aqt.webview
import PyQt6.QtWidgets

sys.path.append('/Users/veyndan/Development/myankiplugin/.venv/lib/python3.9/site-packages')

import rdflib  # noqa: E402
import rdflib.plugins.sparql  # noqa: E402
import rdflib.plugins.sparql.sparql  # noqa: E402


class NoteNotFoundError(Exception):
    """ Note not found. """


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

    config = aqt.mw.addonManager.getConfig(__name__)

    url = next((query['url'] for query in config['urls'] if query['noteTypeId'] == actual_note.mid), None)
    if url is None:
        print('url not found for note type', actual_note.mid)
        return
    actual_url: str = url

    with urllib.request.urlopen(actual_url) as response:
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

    config = aqt.mw.addonManager.getConfig(__name__)

    url = next((query['url'] for query in config['urls'] if query['noteTypeId'] == note.mid), None)
    if url is None:
        print('URL not found for note type', note.mid)
        return note
    actual_url: str = url

    with urllib.request.urlopen(actual_url) as response:
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
        link = editor.urlToLink(value.value) if editor.isURL(value.value) else value.value
        note[label.value] = value.value if link is None else link

    return note


def on_generate_clicked(editor: aqt.editor.Editor):
    note = editor.note
    if note is None:
        print(NoteNotFoundError())
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


def models_did_init_buttons(buttons: list[tuple[str, [[], None]]], models: aqt.models.Models) -> list[tuple[str, [[], None]]]:
    def add_from_url_button_function(col: aqt.Collection) -> None:
        text, url, ok = get_text()
        if not ok:
            return

        with urllib.request.urlopen(url) as response:
            prepared_query = rdflib.plugins.sparql.prepareQuery(response.read())

        initial_graph = rdflib.Graph().query(prepared_query).graph

        query_result_fields = initial_graph.query(
            rdflib.plugins.sparql.prepareQuery(
                textwrap.dedent(
                    '''
                    PREFIX anki: <https://veyndan.com/foo/>
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    
                    SELECT ?fieldLabel WHERE {
                        [] a anki:field;
                            rdfs:label ?fieldLabel.
                    }
                    '''
                )
            )
        )

        notetype = col.models.new(text)

        for binding in query_result_fields:
            label: rdflib.Literal = binding['fieldLabel']
            col.models.add_field(notetype, col.models.new_field(label.value))

        query_result0 = initial_graph.query(
            rdflib.plugins.sparql.prepareQuery(
                textwrap.dedent(
                    '''
                    PREFIX anki: <https://veyndan.com/foo/>
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    
                    SELECT ?templateLabel ?qfmt ?afmt WHERE {
                        [] a anki:template;
                            rdfs:label ?templateLabel;
                            anki:qfmt ?qfmt;
                            anki:afmt ?afmt.
                    }
                    '''
                )
            )
        )

        for binding in query_result0:
            label: rdflib.Literal = binding['templateLabel']
            qfmt: rdflib.Literal = binding['qfmt']
            afmt: rdflib.Literal = binding['afmt']
            col.models.add_template(notetype, col.models.new_template(label.value) | {'qfmt': qfmt.value, 'afmt': afmt.value})

        def on_notetype_added(success: aqt.operations.ResultWithChanges) -> None:
            config = aqt.mw.addonManager.getConfig(__name__)
            config["urls"].append({"noteTypeId": success.id, "url": url})
            aqt.mw.addonManager.writeConfig(__name__, config)
            models.refresh_list()

        aqt.operations.notetype.add_notetype_legacy(parent=models, notetype=notetype) \
            .success(on_notetype_added) \
            .run_in_background()

    anki.stdmodels.models.append(("From URL", add_from_url_button_function))

    return buttons


# TODO Find a more appropriate hook to add the notetype
aqt.gui_hooks.models_did_init_buttons.append(models_did_init_buttons)


# This was heavily copied from aqt.utils.getText
def get_text() -> tuple[str, str, bool]:
    """Returns (string, string, succeeded)."""
    aqt.mw.app.activeWindow().close()
    dialog = GetTextDialog(parent=aqt.mw.app.activeWindow())
    ret = dialog.exec()
    return dialog.name, dialog.url, ret == PyQt6.QtWidgets.QDialog.DialogCode.Accepted


# This was heavily inspired from aqt.utils.GetTextDialog so the UI is similar to the other "Add" mechanisms.
class GetTextDialog(aqt.qt.QDialog):
    def __init__(self, parent: aqt.qt.QWidget) -> None:
        aqt.qt.QDialog.__init__(self, parent)

        self.setWindowModality(aqt.qt.Qt.WindowModality.WindowModal)
        self.setMinimumWidth(400)

        self._layout = aqt.qt.QVBoxLayout()

        self._edit_name = aqt.qt.QLineEdit()
        self._add_input_field(label=aqt.utils.tr.actions_name(), line_edit=self._edit_name)

        self._edit_url = aqt.qt.QLineEdit()
        self._add_input_field(label="URL:", line_edit=self._edit_url)

        dialog_button_box = aqt.qt.QDialogButtonBox(aqt.qt.QDialogButtonBox.StandardButton.Ok | aqt.qt.QDialogButtonBox.StandardButton.Cancel)
        self._layout.addWidget(dialog_button_box)

        self.setLayout(self._layout)

        dialog_button_box.accepted.connect(self.accept)
        dialog_button_box.rejected.connect(self.reject)

    def _add_input_field(self, label: str, line_edit: aqt.qt.QLineEdit) -> None:
        self._layout.addWidget(aqt.qt.QLabel(label))
        self._layout.addWidget(line_edit)

    @property
    def name(self) -> str:
        return str(self._edit_name.text())

    @property
    def url(self) -> str:
        return str(self._edit_url.text())

    def accept(self) -> None:
        if self.name.strip() != '' and self.url.strip() != '':
            return aqt.qt.QDialog.accept(self)
        else:
            self.reject()

    def reject(self) -> None:
        return aqt.qt.QDialog.reject(self)
