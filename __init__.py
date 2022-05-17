import urllib.request
import sys
import textwrap
import typing

import anki.hooks
import anki.notes
import aqt.deckbrowser
import aqt.editor
import aqt.models
import aqt.operations.notetype
import aqt.utils
import aqt.operations
import aqt.operations.note
import aqt.qt
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


# TODO Fix the below. We need to add a new note type so the user can base their new note type on ours. When the user
#  clicks our note type (e.g., "myankiplugin: From URL…"), we display TWO fields. One is the normal field that currently
#  shows up which is the "name". We need to add ANOTHER field which is the "URL" field. When the user inputs this field,
#  we just update the meta.json file with the value. At a later point, we MIGHT need a way to edit the URL (though idk
#  why atm). We do this by the following the first part, but the second part we'll need to somehow hook in to the file
#  aqt/models.py at Models#add.

# TODO [UPDATE] This looks weird. We are actually adding a new dummy note type for no real reason. Instead perhaps just
#  add a "Add from URL…" button on the "Note Types" dialog? Then can just continue doing the rest of what I said, and it
#  should be easier as I'm creating a new dialog instead of trying to hook into a dialog which doesn't want to be edited.
# def deck_browser_did_render(deck_browser: aqt.deckbrowser.DeckBrowser) -> None:
#     notetype = deck_browser.mw.col.models.new("myankiplugin")
#     deck_browser.mw.col.models.add_field(notetype, deck_browser.mw.col.models.new_field("Whatever"))
#     deck_browser.mw.col.models.add_template(notetype, deck_browser.mw.col.models.new_template("Something") | {'qfmt': '{{Whatever}}'})
#     deck_browser.mw.col.models.add_dict(notetype)


# aqt.gui_hooks.deck_browser_did_render.append(deck_browser_did_render)

# TODO In anki.stdmodels there's a global 'models' variable which could be useful and has the description:
#  > add-on authors can add ("note type name", function) to this list to have it shown in the add/clone note type screen


def models_did_init_buttons(buttons: list[tuple[str, [[], None]]], models: aqt.models.Models) -> list[tuple[str, [[], None]]]:
    add_button_index = next(index for index in range(len(buttons)) if buttons[index][0] == aqt.utils.tr.actions_add())

    def add_from_url_button_function():
        text, url, ok = get_text(aqt.utils.tr.actions_name())
        if not ok or not text.strip():
            return

        with urllib.request.urlopen(url) as response:
            prepared_query = rdflib.plugins.sparql.prepareQuery(response.read())

        initial_graph = rdflib.Graph().query(prepared_query).graph

        query_result = initial_graph.query(
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

        # TODO Here we'd call out to the url that the user specified. We query it with an empty model to get the fields.
        #  With the template I think we should just set a default for now, though we COULD specify it in the query somehow,
        #  though idk if this actually makes sense or not. If it doesn't, perhaps we can default to the "Basic" notetype
        #  query format just to have something half decent and is at least familiar to the user (instead of me creating
        #  some new note type that people will have to learn to be a starting point).
        notetype = models.mw.col.models.new(text)

        for binding in query_result:
            label: rdflib.Literal = binding['fieldLabel']
            models.mw.col.models.add_field(notetype, models.mw.col.models.new_field(label.value))

        models.mw.col.models.add_template(notetype, models.mw.col.models.new_template("Something"))

        # TODO Before we add the new note type, make sure to update the meta.json (its current format is fine for now).

        aqt.operations.notetype.add_notetype_legacy(parent=models, notetype=notetype) \
            .success(models.refresh_list) \
            .run_in_background()

    import anki.stdmodels
    anki.stdmodels.models.append(("Add from URL", add_from_url_button_function))

    buttons.insert(add_button_index + 1, ("Add from URL", add_from_url_button_function))
    return buttons


aqt.gui_hooks.models_did_init_buttons.append(models_did_init_buttons)


# This was heavily copied from aqt.utils.getText
def get_text(prompt: str, title: str = "Anki") -> tuple[str, str, int]:
    """Returns (string, succeeded)."""
    parent = aqt.mw.app.activeWindow() or aqt.mw
    d = GetTextDialog(parent, prompt, title=title)
    d.setWindowModality(aqt.qt.Qt.WindowModality.WindowModal)
    ret = d.exec()
    return str(d.l.text()), str(d.edit_url.text()), ret


# This was heavily copied from aqt.utils.GetTextDialog
class GetTextDialog(aqt.qt.QDialog):
    def __init__(self, parent: aqt.qt.QWidget, question: str, title: str = "Anki") -> None:
        aqt.qt.QDialog.__init__(self, parent)
        self.setWindowTitle(title)
        aqt.utils.disable_help_button(self)
        self.question = question
        self.qlabel = aqt.qt.QLabel(question)
        self.setMinimumWidth(400)
        v = aqt.qt.QVBoxLayout()

        v.addWidget(self.qlabel)
        edit_name = aqt.qt.QLineEdit()
        self.l = edit_name  # TODO We need this, probably because we're inheriting from aqt.qt.QDialog which looks like an Anki specific dialog.
        v.addWidget(self.l)

        v.addWidget(aqt.qt.QLabel("URL"))
        self.edit_url = aqt.qt.QLineEdit()
        v.addWidget(self.edit_url)

        buts = (aqt.qt.QDialogButtonBox.StandardButton.Ok | aqt.qt.QDialogButtonBox.StandardButton.Cancel)
        b = aqt.qt.QDialogButtonBox(buts)  # type: ignore
        v.addWidget(b)
        self.setLayout(v)
        aqt.qt.qconnect(b.button(aqt.qt.QDialogButtonBox.StandardButton.Ok).clicked, self.accept)
        aqt.qt.qconnect(b.button(aqt.qt.QDialogButtonBox.StandardButton.Cancel).clicked, self.reject)

    def accept(self) -> None:
        return aqt.qt.QDialog.accept(self)

    def reject(self) -> None:
        return aqt.qt.QDialog.reject(self)
