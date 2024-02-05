import anki.notes
import rdflib


def to_graph(note: anki.notes.Note) -> rdflib.Graph:
    fields_state_initial = rdflib.Graph()
    for (label, value) in note.items():
        import uuid
        field_subject = rdflib.URIRef('https://veyndan.com/foo/' + uuid.uuid4().hex)  # TODO For some reason I can't use blank node
        fields_state_initial \
            .add((field_subject, rdflib.RDF.type, rdflib.URIRef('https://veyndan.com/foo/field'))) \
            .add((field_subject, rdflib.RDFS.label, rdflib.Literal(label))) \
            .add((field_subject, rdflib.RDF.value, rdflib.Literal(value)))
    return fields_state_initial
