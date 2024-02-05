import anki.notes
import aqt.editor
import rdflib.plugins.sparql
import textwrap


# This feels wrong having to pass in an editor and a note to convert TO a note. What we're
# really doing here is converting a graph to a set of fields. We could instead return those
# fields without having to pass in a note, and join it at the invocation site with
# note.note_type()["flds"] like note.set_fields(note.note_type()["flds"] | to_fields(graph, editor)).
# However, note has the function __setitem__ which easily manipulates a field's value, and as I
# don't want to fight the APIs, I'm kind of stuck with this. A potential saving grace is that
# anki.models.NotetypeDict (which is what note.note_type() returns) is marked as "legacy", though
# I'm not too sure what its replacement is.
def to_note(graph: rdflib.Graph, editor: aqt.editor.Editor, note: anki.notes.Note) -> anki.notes.Note:
    query_result = graph.query(
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

    for binding in query_result:
        label: rdflib.Literal = binding['fieldLabel']
        value: rdflib.Literal = binding['fieldValue']
        link = editor.urlToLink(value.value) if editor.isURL(value.value) else value.value
        note[label.value] = value.value if link is None else link

    return note
