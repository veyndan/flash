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

import pyshacl  # noqa: E402
import rdflib  # noqa: E402
import rdflib.plugins.sparql  # noqa: E402
import rdflib.plugins.sparql.sparql  # noqa: E402


def fields_as_graph(note: anki.notes.Note) -> rdflib.Graph:
    graph = rdflib.Graph()
    for (label, value) in note.items():
        import uuid
        field_subject = rdflib.URIRef('https://veyndan.com/foo/' + uuid.uuid4().hex)  # TODO For some reason I can't use blank node
        graph \
            .add((field_subject, rdflib.RDF.type, rdflib.URIRef('https://veyndan.com/foo/field'))) \
            .add((field_subject, rdflib.RDFS.label, rdflib.Literal(label))) \
            .add((field_subject, rdflib.RDF.value, rdflib.Literal(value)))
    return graph


class NoteNotFoundError(Exception):
    """ Note not found. """


class InvalidConfig(Exception):
    """ Config is invalid. """


class Config:
    def __init__(self):
        self._graph = rdflib.Graph()
        with open("user_files/config.ttl") as config_file:
            self._graph = self._graph.parse(file=config_file)

    def add_note(self, note_type_id: int, url: str):
        node = rdflib.BNode()
        self._graph.add((node, rdflib.namespace.RDF.type, rdflib.URIRef("https://veyndan.com/foo/Note")))
        self._graph.add((node, rdflib.URIRef("https://veyndan.com/foo/noteTypeId"), rdflib.Literal(note_type_id, datatype=rdflib.namespace.XSD.string)))
        self._graph.add((node, rdflib.URIRef("https://veyndan.com/foo/url"), rdflib.URIRef(url)))
        with open("user_files/config.ttl", "w") as config_file:
            config_file.write(self._graph.serialize(format="turtle"))

    def query_from_note(self, note: anki.notes.Note) -> typing.Optional[rdflib.plugins.sparql.sparql.Query]:
        prepared_query_url = rdflib.plugins.sparql.prepareQuery(
            textwrap.dedent(
                '''
                PREFIX anki: <https://veyndan.com/foo/>
                
                SELECT ?url WHERE {
                    [] a anki:Note;
                        anki:noteTypeId ?noteTypeId;
                        anki:url ?url.
                }
                '''
            )
        )
        query_result = self._graph.query(prepared_query_url, initBindings={'noteTypeId': rdflib.Literal(note.mid, datatype=rdflib.namespace.XSD.string)})
        if len(query_result) == 0:
            print('url not found for note type', note.mid)
            return None
        if len(query_result) > 1:
            aqt.utils.showCritical("myankiplugin internal files are corrupt. Multiple query URLs associated with note which is invalid.")
            raise InvalidConfig()
        with urllib.request.urlopen(query_result.bindings[0]['url']) as response:
            prepared_query = rdflib.plugins.sparql.prepareQuery(response.read())
        return prepared_query


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

    config = Config()

    try:
        prepared_query = config.query_from_note(actual_note)
        if prepared_query is None:
            return
    except InvalidConfig:
        return

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
    fields_state_initial = fields_as_graph(note)

    config = Config()

    try:
        prepared_query = config.query_from_note(note)
        if prepared_query is None:
            return note
    except InvalidConfig:
        return note

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
        note[label.value] = editor.urlToLink(value.value) if editor.isURL(value.value) else value.value

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


aqt.mw.addonManager.setWebExports(__name__, r"(web|icons)/.*\.(js|css|png)")


def add_generate_button(web_content: aqt.webview.WebContent, context: typing.Optional[object]) -> None:
    if not isinstance(context, aqt.editor.Editor):
        return

    addon_package = context.mw.addonManager.addonFromModule(__name__)
    base_path = f"/_addons/{addon_package}/web"

    web_content.js.append(f"{base_path}/editor.js")
    web_content.css.append(f"{base_path}/editor.css")


aqt.gui_hooks.webview_will_set_content.append(add_generate_button)


def webview_did_receive_js_message(handled: tuple[bool, typing.Any], message: str, context: typing.Any) -> tuple[bool, typing.Any]:
    if not isinstance(context, aqt.editor.Editor) or not message == 'myankiplugin:generate':
        return handled

    on_generate_clicked(context)
    return True, None


aqt.gui_hooks.webview_did_receive_js_message.append(webview_did_receive_js_message)


def models_did_init_buttons(buttons: list[tuple[str, [[], None]]], models: aqt.models.Models) -> list[tuple[str, [[], None]]]:
    def add_from_url_button_function(col: aqt.Collection) -> None:
        text, url, ok = get_text()
        if not ok:
            return

        with urllib.request.urlopen(url) as response:
            prepared_query = rdflib.plugins.sparql.prepareQuery(response.read())

        initial_graph = rdflib.Graph().query(prepared_query).graph

        conforms, results_graph, results_text = pyshacl.validate(
            initial_graph,
            shacl_graph='http://localhost:9090/shapesGraph.ttl',
        )

        if not conforms:
            aqt.utils.showCritical(
                f'''
                Graph doesn't conform to specification.
                
                Please contact the developer and copy-paste the following message to them.
                
                {results_text}
                '''
            )
            return

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
            config = Config()
            config.add_note(note_type_id=success.id, url=url)
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
