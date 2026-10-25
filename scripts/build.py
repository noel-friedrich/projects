"""Run with python3 scripts/build.py to rebuild the static project pages."""

import json
import os
import re
import unicodedata
from html import escape
from pathlib import Path
from string import Template
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent.parent


def slugify(name):
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def anchor(name, url, new_tab=False, transition_name=None):
    attributes = ' target="_blank" rel="noopener noreferrer"' if new_tab else ""
    if transition_name:
        attributes += f' style="view-transition-name: {escape(transition_name, quote=True)}"'
    return f'<a href="{escape(url, quote=True)}"{attributes}>{escape(name)}</a>'


def build():
    nodes = json.loads((ROOT / "project-nodes.json").read_text(encoding="utf-8"))
    template = Template((ROOT / "scripts/template.html").read_text(encoding="utf-8"))
    pages = {}
    children = {node["name"]: [] for node in nodes}

    for node in nodes:
        name = node["name"]
        slug = slugify(name)
        page = Path("index.html") if name == "Projects" else Path("p") / slug / "index.html"
        if not slug or name in pages or page in pages.values():
            raise ValueError(f"Empty or duplicate page name: {name}")
        pages[name] = page

    if [node["name"] for node in nodes if not node["parents"]] != ["Projects"]:
        raise ValueError("Projects must be the only parentless node")

    for node in nodes:
        for parent in node["parents"]:
            if parent not in children:
                raise ValueError(f"Unknown parent {parent!r} for {node['name']!r}")
            children[parent].append(node["name"])

    def descendants(name):
        result = set(children[name])
        for child in children[name]:
            result.update(descendants(child))
        return result

    descendant_counts = {name: len(descendants(name)) for name in children}

    for node in nodes:
        page = pages[node["name"]]

        def node_link(name):
            count = descendant_counts[name]
            label = f"{name} [{count}]" if count else name
            return anchor(label, os.path.relpath(pages[name].parent, page.parent) + "/", transition_name="node-" + slugify(name))

        metadata = "\n".join(
            f"<dt>{escape('Last updated on' if key == 'last-update-date' else key.replace('-', ' ').capitalize())}</dt><dd>{escape(str(value))}</dd>"
            for key, value in node.items()
            if key not in {"name", "parents", "description", "links"}
        )
        links = []
        for link in node.get("links", []):
            url = link.get("url", "")
            if url and not urlsplit(url).scheme:
                url = "https://" + url.lstrip("/")
            content = anchor(link["name"], url, new_tab=True) if url else escape(link["name"])
            links.append(f"<li>{content}</li>")
        html = template.substitute(
            name=escape(node["name"]),
            transition_name="node-" + slugify(node["name"]),
            parents="\n".join(node_link(name) for name in node["parents"]) or escape("<no parent pages>"),
            metadata=metadata,
            description=escape(node["description"]).replace("\n", "<br>\n"),
            links="\n".join(links),
            children="\n".join(f"<li>{node_link(name)}</li>" for name in children[node["name"]]),
        )
        destination = ROOT / page
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(html, encoding="utf-8")

    print(f"Built {len(nodes)} pages.")


if __name__ == "__main__":
    build()
