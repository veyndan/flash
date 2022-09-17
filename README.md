# myankiplugin

> :warning: myankiplugin is in alpha.
> Backwards incompatible changes are likely and can break without notice.

[//]: # (myankiplugin is an [Anki]&#40;https://apps.ankiweb.net/&#41; add-on that can autofill fields when adding new notes.)
myankiplugin is an [Anki](https://apps.ankiweb.net/) add-on that removes the tediousness of creating flashcards, by using queries from around the web to autofill as many fields as possible.

https://user-images.githubusercontent.com/6900601/190874661-24577ed5-3c4c-4b4b-8765-66f3abc89ad3.mp4

## Install

### One-time setup

To setup, just clone the repo and install the required dependencies.

```bash
git clone https://github.com/veyndan/myankiplugin.git
cd myankiplugin
python3 -m venv .venv
source .venv/bin/activate 
python -m pip install -r requirements.txt
```

### Run Anki

```bash
yarn --cwd "./ts" && yarn --cwd "./ts" build && DISABLE_QT5_COMPAT=1 ./.venv/bin/anki -p Playground
```

To check that the add-on is correctly installed, go to `Tools > Add-ons`, and you should see `myankiplugin` listed among them.

To upgrade, just run `git pull` while in the `myankiplugin` directory, and restart your Anki program.

## Usage

To begin using myankiplugin, you first need to associate a query URL with a note type.

To add a new note type:

- Go to `Tools > Manage Note Types`
- Click `Add`
- Click `Add: From URL`
- Insert a name for the new note type. This can be anything you want.
- Copy-paste the `Query URL` below for whichever query you want
- Click `OK`

Once you've added the new note type, you can just add a new note as normal, and make sure that the new note type is selected in the note editor view.
You will see that some fields are suffixed with `[REQUIRED]`.
These fields are required to be filled out.
Once you've filled out these fields, hit the `Generate` button in the toolbar.
After a short while, the note should be automatically populated!

### Available Queries

The following are queries that you can use to start generating Anki notes.

- [ ] I should probably move the English to German translation query somewhere else, and somewhere a bit more permanent. The issue with keeping it here and the moving it, is that I'd need to maintain redirects if anyone actually used it, and I know I don't like it here.
- [ ] I can probably move the Uppercase text one too. It can probably just stay in the same repo though as it's a demo. Tbh I don't know if I like it there, but it is useful to have a dummy API that should always work and people can quickly jump off of.

| Description                                              | Input                                              | Output                                                                                                                                                              | Query URL                                                                  |
|----------------------------------------------------------|----------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|
| Translate from English nouns to German nouns             | <ul><li>English noun</li><li>German noun</li></ul> | <ul><li>English plural</li><li>English example sentence</li><li>German plural</li><li>German grammatical genders</li><li>German pronunciation audio files</li></ul> | https://raw.githubusercontent.com/veyndan/myankiplugin/master/uppercase.rq |
| Uppercase text (practically useless, but good for demos) | Arbitrary text                                     | Your text in uppercase                                                                                                                                              | https://raw.githubusercontent.com/veyndan/myankiplugin/master/uppercase.rq |

## Custom Query Development

If you need notes that can't be generated via the above queries (which is likely), then you'll need to develop your own query.

Queries are written in SPARQL and must be available via a URL.
To get started, have a look at how the queries in [Available Queries](#available-queries) are developed.
At the moment, there is a large usage of Wikidata, but any service that provides a SPARQL interface can be used.
The query should be valid against [this SHACL graph](https://github.com/veyndan/myankiplugin/blob/master/shapesGraph.ttl).
Note that all queries are validated when adding a new note type via `Add: From URL` (per the [Usage](#usage) section).

While developing the query, it's useful to host it via `localhost`.
If you then wish to share the query with the rest of the world, you'll need to host it somewhere (e.g., your own domain, GitHub).

If you face any issues surrounding query creation, please file an issue.
Changing the API now is a lot easier than when we hit a 1.0 release.
