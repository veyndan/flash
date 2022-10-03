import pathlib
import typing
import urllib.request

import anki.hooks
import anki.models
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
import pyshacl
import rdflib
import rdflib.plugins.sparql
import rdflib.plugins.sparql.sparql


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


class NoteNotFoundError(Exception):
    """Note not found."""


class InvalidConfig(Exception):
    """Config is invalid."""


class Config:
    def __init__(self):
        user_files_path = pathlib.Path.cwd() / "user_files"
        user_files_path.mkdir(exist_ok=True)
        self._path = user_files_path / "config.ttl"
        self._path.touch(exist_ok=True)
        self._graph = rdflib.Graph()
        with open(self._path) as config_file:
            self._graph = self._graph.parse(file=config_file)

    def add_note(self, note_type_id: int, url: str):
        self._graph.update(
            f"""
            PREFIX anki: <https://veyndan.com/foo/> 
            
            INSERT DATA {{
                [] a anki:Note;
                    anki:noteTypeId {rdflib.Literal(note_type_id, datatype=rdflib.namespace.XSD.string).n3()};
                    anki:url {rdflib.URIRef(url).n3()}.
            }}
            """,
        )
        with open(self._path, "w") as config_file:
            config_file.write(self._graph.serialize(format="turtle"))

    def query_from_note(
        self,
        note: anki.notes.Note,
    ) -> rdflib.plugins.sparql.sparql.Query | None:
        query_result = self._graph.query(
            f"""
            PREFIX anki: <https://veyndan.com/foo/>
            
            SELECT ?url WHERE {{
                [] a anki:Note;
                    anki:noteTypeId {rdflib.Literal(note.mid, datatype=rdflib.namespace.XSD.string).n3()};
                    anki:url ?url.
            }}
            """,
        )
        if len(query_result) == 0:
            print("url not found for note type", note.mid)
            return None
        if len(query_result) > 1:
            aqt.utils.showCritical(
                "Flash internal files are corrupt. Multiple query URLs associated with note which is invalid."
            )
            raise InvalidConfig()
        with urllib.request.urlopen(query_result.bindings[0]["url"]) as response:
            prepared_query = rdflib.plugins.sparql.prepareQuery(response.read())
        return prepared_query


def map_note(
    editor: aqt.editor.Editor,
    note: anki.notes.Note,
    on_generate_clicked: bool,
) -> anki.notes.Note:
    """
    Add hints to the GUI to get the initial state of the note into a form (fields_state_initial) that can be parsed by
    Flash.
    """
    fields_state_initial = fields_as_graph(note.items(), on_generate_clicked)

    config = Config()

    try:
        prepared_query = config.query_from_note(note)
        if prepared_query is None:
            return note
    except InvalidConfig:
        return note

    query_result = fields_state_initial.query(prepared_query)

    query_result_field_required = query_result.graph.query(
        """
        PREFIX anki: <https://veyndan.com/foo/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?fieldLabel WHERE {
            [] a anki:field;
                anki:required true;
                rdfs:label ?fieldLabel.
        }
        """
    )

    for label in [binding["fieldLabel"] for binding in query_result_field_required]:
        label_value: str = label.value

        editor.web.page().runJavaScript(
            f"""
            [...document.querySelectorAll('.label-name')]
                .filter(field_name => field_name.innerHTML === '{label_value}')
                .forEach(field_name => field_name.insertAdjacentText('afterend', ' [Required]'));
            """
        )

    query_result2 = query_result.graph.query(
        """
        PREFIX anki: <https://veyndan.com/foo/>
        
        SELECT ?fieldLabel ?fieldValue WHERE {
            [] a anki:field;
                rdfs:label ?fieldLabel;
                rdf:value ?fieldValue.
        }
        """
    )

    for binding in query_result2:
        label2: rdflib.Literal = binding["fieldLabel"]
        value2: rdflib.Literal = binding["fieldValue"]
        print(f"({label2}, {value2})")
        note[label2.value] = (
            editor.urlToLink(value2.value)
            if editor.isURL(value2.value)
            else value2.value
        )

    return note


def on_ui_modification(
    editor: aqt.editor.Editor,
    note: anki.notes.Note,
    on_generate_clicked: bool,
):
    query_op = aqt.operations.QueryOp(
        parent=editor.mw,
        op=lambda col: map_note(editor, note, on_generate_clicked),
        success=editor.set_note,
    )

    query_op.with_progress().run_in_background()


aqt.mw.addonManager.setWebExports(__name__, r"(web|icons)/.*\.(js|css|png)")


def add_generate_button(
    web_content: aqt.webview.WebContent,
    context: object | None,
) -> None:
    if not isinstance(context, aqt.editor.Editor):
        return

    addon_package = context.mw.addonManager.addonFromModule(__name__)
    base_path = f"/_addons/{addon_package}/web"

    web_content.js.append(f"{base_path}/editor.js")
    web_content.css.append(f"{base_path}/editor.css")


aqt.gui_hooks.webview_will_set_content.append(add_generate_button)


def webview_did_receive_js_message(
    handled: tuple[bool, typing.Any],
    message: str,
    context: typing.Any,
) -> tuple[bool, typing.Any]:
    if isinstance(context, aqt.editor.Editor) and message == "flash:generate":
        note = context.note
        if note is None:
            print(NoteNotFoundError())
            aqt.utils.showInfo("No note found.")
        else:
            on_ui_modification(context, note, on_generate_clicked=True)
        return True, None
    if isinstance(context, aqt.editor.Editor) and message.startswith("key:"):
        # TODO There's an artificial delay between key press and receiving the message.
        # TODO The editor.note is updated after this conditional is executed, so we always have the prior note state.
        #  Currently just manually constructing the note with the new fields and passing it.
        note = context.note
        if note is None:
            print(NoteNotFoundError())
            aqt.utils.showInfo("No note found.")
        else:
            field_index = int(message.split(":")[1])
            field_text = message.split(":")[3]
            note[note.keys()[field_index]] = field_text
            on_ui_modification(context, note, on_generate_clicked=False)
        return True, None

    return handled


aqt.gui_hooks.webview_did_receive_js_message.append(webview_did_receive_js_message)


def models_did_init_buttons(
    buttons: typing.List[tuple[str, typing.Callable[[], None]]],
    models: aqt.models.Models,
) -> typing.List[tuple[str, typing.Callable[[], None]]]:
    def add_from_url_button_function(col: aqt.Collection) -> anki.models.NotetypeDict:
        text, url, ok = get_text()
        if not ok:
            return

        with urllib.request.urlopen(url) as response:
            initial_graph = rdflib.Graph().query(response.read()).graph

        conforms, results_graph, results_text = pyshacl.validate(
            initial_graph,
            shacl_graph="http://localhost:9090/flash/shapesGraph.ttl",
        )

        if not conforms:
            aqt.utils.showCritical(
                f"""
                Graph doesn't conform to specification.
                
                Please contact the developer and copy-paste the following message to them.
                
                {results_text}
                """
            )
            return

        query_result_fields = initial_graph.query(
            """
            PREFIX anki: <https://veyndan.com/foo/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT ?fieldLabel WHERE {
                [] a anki:field;
                    rdfs:label ?fieldLabel.
            }
            """
        )

        notetype = col.models.new(text)

        for binding in query_result_fields:
            label: rdflib.Literal = binding["fieldLabel"]
            col.models.add_field(notetype, col.models.new_field(label.value))

        query_result0 = initial_graph.query(
            """
            PREFIX anki: <https://veyndan.com/foo/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT ?templateLabel ?qfmt ?afmt WHERE {
                [] a anki:template;
                    rdfs:label ?templateLabel;
                    anki:qfmt ?qfmt;
                    anki:afmt ?afmt.
            }
            """
        )

        for binding in query_result0:
            label0: rdflib.Literal = binding["templateLabel"]
            qfmt: rdflib.Literal = binding["qfmt"]
            afmt: rdflib.Literal = binding["afmt"]
            col.models.add_template(
                notetype,
                col.models.new_template(label0.value)
                | {"qfmt": qfmt.value, "afmt": afmt.value},
            )

        success = col.models.add_dict(notetype)
        config = Config()
        config.add_note(note_type_id=success.id, url=url)
        models.refresh_list()

        return col.models.get(success.id)

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
        self._add_input_field(
            label=aqt.utils.tr.actions_name(),
            line_edit=self._edit_name,
        )

        self._edit_url = aqt.qt.QLineEdit()
        self._add_input_field(label="URL:", line_edit=self._edit_url)

        dialog_button_box = aqt.qt.QDialogButtonBox(
            aqt.qt.QDialogButtonBox.StandardButton.Ok
            | aqt.qt.QDialogButtonBox.StandardButton.Cancel
        )
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
        if self.name.strip() != "" and self.url.strip() != "":
            return aqt.qt.QDialog.accept(self)
        else:
            self.reject()

    def reject(self) -> None:
        return aqt.qt.QDialog.reject(self)
