"""mkdocs-categories-plugin

An MkDocs plugin allowing for categorization of pages in your wiki.
"""

from __future__ import annotations

import logging
import re
import shutil
import unicodedata
from logging import Logger, getLogger
from pathlib import Path

from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File
from mkdocs.structure.pages import Page
from mkdocs.utils import get_markdown_title, get_relative_url, meta
from natsort import natsorted


def get_page_title(page_src: str, meta_data: dict) -> str:
    """Returns the title of the page. The title in the meta data section
    will take precedence over the H1 markdown title if both are provided."""
    return str(
        meta_data["title"]
        if "title" in meta_data and isinstance(meta_data["title"], str)
        else get_markdown_title(page_src) or ""
    )


def slugify(title: str) -> str:
    """Returns the path slug used for the category URL.
    Adapted from django.utils.text"""
    slug = (
        unicodedata.normalize("NFKD", str(title))
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    slug = re.sub(r"[^\w\s-]", "", slug).strip().lower()
    return re.sub(r"[-\s]+", "-", slug)


class CategoriesPlugin(BasePlugin):
    """
    Defines the exported MkDocs plugin class and all its functionality.
    """

    config_scheme = (
        ("generate_index", config_options.Type(bool, default=True)),
        ("verbose", config_options.Type(bool, default=False)),
        ("no_nav", config_options.Type(bool, default=False)),
        ("base_name", config_options.Type(str, default="categories")),
        ("section_title", config_options.Type(str, default="Categories")),
        ("category_separator", config_options.Type(str, default="|")),
        ("debug_fs", config_options.Type(bool, default=False)),
        ("show_breadcrumbs", config_options.Type(bool, default=False)),
        ("breadcrumb_separator", config_options.Type(str, default=">")),
    )
    log: Logger = getLogger(f"mkdocs.plugins.{__name__}")
    categories: dict = {}
    pages: dict = {}
    cat_path: Path = Path()

    def on_config(self, _):
        """Set the log level if the verbose config option is set"""
        self.log.setLevel(logging.INFO if self.config["verbose"] else logging.WARNING)
        self.cat_path = Path(self.config["base_name"])
        if self.cat_path.exists():
            self.clean_temp_dir()
        self.cat_path.mkdir(parents=True)

    def clean_temp_dir(self):
        """Remove the temporary directory after execution."""
        if self.config["debug_fs"]:
            self.log.info("Debugging: Not removing temporary directory.")
            return
        shutil.rmtree(self.cat_path)

    def on_nav(self, nav, /, **_):
        """
        Executed when the navigation is created. If the config option no_nav
        is set to true, the categories section will be removed from the global
        navigation.
        """
        if not self.config["no_nav"]:
            return nav
        for item in nav:
            if item.is_section and str(item.title).lower() == self.config["base_name"]:
                nav.items.remove(item)
                break
        return nav

    def on_build_error(self, **_):
        """Executed after the build has failed."""
        self.categories.clear()
        self.pages.clear()
        self.clean_temp_dir()

    def on_post_build(self, **_):
        """Executed after the build has successfully completed."""
        self.log.info("Defined %s categories.", len(self.categories))
        self.categories.clear()
        self.pages.clear()
        self.clean_temp_dir()

    def on_page_markdown(self, markdown: str, /, *, page: Page, **_):
        """Appends the category links section for a page to the markdown."""
        relative_url = get_relative_url(str(self.cat_path), page.file.src_uri)
        if page.file.src_uri not in self.pages:
            return markdown
        breadcrumb_separator = f" {self.config['breadcrumb_separator']} "
        links = list(
            map(
                lambda c: (
                    (
                        f"- {breadcrumb_separator.join(self.get_breadcrumb_links(c, relative_url))}"
                    )
                    if self.config["show_breadcrumbs"]
                    else (
                        f"- [{self.categories[c]['name']}]"
                        f"({relative_url}/{self.categories[c]['slug']}.md)"
                    )
                ),
                natsorted(self.pages[page.file.src_uri]),
            )
        )
        return markdown + f"\n## {self.config['section_title']}\n\n" + "\n".join(links)

    def get_breadcrumb_keys(self, category_key: str) -> list[str]:
        """Return category lineage keys from root to the given category."""
        lineage = []
        current_key = category_key
        while current_key is not None and current_key in self.categories:
            lineage.append(current_key)
            current_key = self.categories[current_key]["parent"]
        lineage.reverse()
        return lineage

    def get_breadcrumb_links(self, category_key: str, relative_url: str) -> list[str]:
        """Return markdown links for each category in the lineage."""
        return list(
            map(
                lambda key: (
                    f"[{self.categories[key]['name']}]"
                    f"({relative_url}/{self.categories[key]['slug']}.md)"
                ),
                self.get_breadcrumb_keys(category_key),
            )
        )

    def ensure_path(self, cat_path: list[str]) -> dict | None:
        """Ensure that the category path exists and return the last category."""
        if len(cat_path) <= 0:
            return None
        result = {}
        for i, cat_name in enumerate(cat_path):
            cat_key = "-".join(cat_path[: i + 1])
            if cat_key not in self.categories:
                slugified = slugify(cat_key)
                self.categories[cat_key] = {
                    "name": cat_name,
                    "key": cat_key,
                    "slug": slugify(cat_key),
                    "pages": [],
                    "parent": "-".join(cat_path[:i]) if i > 0 else None,
                    "children": [],
                }
                self.log.info(
                    'Defined new category "%s" with slug "%s"', cat_path[i], slugified
                )
            if len(result) > 0 and cat_key not in result["children"]:
                result["children"].append(cat_key)
            result = self.categories[cat_key]
        return result

    def register_page(
        self, cat_path: list[str], page_url: str, page_title: str
    ) -> None:
        """Register a page and, if it does not exist, its category."""
        # Each category stores which pages belong to it
        category = self.ensure_path(cat_path)
        category["pages"].append({"title": page_title, "url": page_url})

        # Each page also stores which categories it belongs to
        if page_url not in self.pages:
            self.pages[page_url] = set()
        self.pages[page_url].add(category["key"])

    def define_categories(self, files) -> None:
        """Read all of the meta data and define any categories."""
        for file in filter(lambda f: f.is_documentation_page(), files):
            with open(file.abs_src_path, encoding="utf-8") as handle:
                source, meta_data = meta.get_data(handle.read())
                if len(meta_data) <= 0 or "categories" not in meta_data:
                    continue
                if not isinstance(meta_data["categories"], list):
                    self.log.error(
                        "The categories object at %s was not a list, but %s",
                        str(file.src_path),
                        type(meta_data["categories"].__name__),
                    )
                    continue
                for category in meta_data["categories"]:
                    self.register_page(
                        str(category).split(self.config["category_separator"]),
                        str(file.src_path),
                        get_page_title(source, meta_data),
                    )

    def get_category_by_parent(self, parent_key: str | None) -> list[dict]:
        """Returns a list of categories with the given parent key."""
        return list(
            filter(lambda c: c["parent"] == parent_key, self.categories.values())
        )

    def render_category_hierarchy(self, parent_key: str | None, indent_level: int = 0) -> list[str]:
        """Recursively renders categories and their children with proper indentation."""
        lines = []
        children = self.get_category_by_parent(parent_key)
        sorted_children = natsorted(children, key=lambda c: c["name"])

        for category in sorted_children:
            # doesn't work with only two spaces...
            indent = "    " * indent_level
            link = f"[{category['name']}](./{category['slug']}.md)"
            page_count = f" ({len(category['pages'])})"
            lines.append(f"{indent}- {link}{page_count}")

            # Recursively render children
            lines.extend(self.render_category_hierarchy(category["key"], indent_level + 1))

        return lines

    def generate_index(self, config) -> File:
        """Generates a categories index page if the option is set."""
        hierarchy_lines = self.render_category_hierarchy(None)
        joined = "\n".join(hierarchy_lines)
        # log the hierarchy if verbose logging is enabled
        if self.config["verbose"]:
            self.log.info("Generated category hierarchy:\n%s", joined)

        with open(self.cat_path / "index.md", mode="w", encoding="utf-8") as file:
            file.write(
                "# All Categories\n\n"
                "\n"
                f"There are a total of {len(self.categories.keys())} categories(s):\n"
                "\n"
                f"{joined}\n"
            )
        return File(
            path=str(self.cat_path / "index.md"),
            src_dir=str(self.cat_path.parent),
            dest_dir=config["site_dir"],
            use_directory_urls=True,
        )

    def render_all_categories_link(self) -> str:
        """Generates a link to the categories index page if the option is set"""
        return (
            ""
            if not self.config["generate_index"]
            else "[All Categories](./index.md)\n\n"
        )

    def render_child_categories(self, category: dict) -> tuple[bool, str]:
        """Renders the child categories of a category."""
        if len(category["children"]) <= 0:
            return False, None
        joined = "\n".join(
            map(
                lambda c: (
                    f"- [{self.categories[c]['name']}](./{self.categories[c]['slug']}.md)"
                ),
                natsorted(category["children"]),
            )
        )
        return True, joined

    def render_category_pages(self, category: dict) -> tuple[bool, str]:
        """Renders the pages of a category."""
        if len(category["pages"]) <= 0:
            return False, None
        joined = "\n".join(
            map(
                lambda p: f"- [{p['title']}](../{p['url']})",
                natsorted(category["pages"], key=lambda p: p["title"]),
            )
        )
        return True, joined

    def render_parent_category(self, category: dict) -> str:
        """Renders the parent category of a category."""
        if not category["parent"]:
            return None
        parent = self.categories[category["parent"]]
        return f"[{parent['name']}](./{parent['slug']}.md)"

    def on_files(self, files, /, *, config, **_):
        """When MkDocs loads its files, load any defined categories."""
        self.define_categories(files)
        for category in self.categories.values():
            file_name = f"{category['slug']}.md"
            (has_pages, pages) = self.render_category_pages(category)
            (has_children, children) = self.render_child_categories(category)
            parent = self.render_parent_category(category)

            with open(self.cat_path / file_name, mode="w", encoding="utf-8") as file:
                file.write(
                    "".join(
                        [
                            f"# Category: {category['name']}\n\n",
                            (f"Parent category: {parent}\n\n" if parent else ""),
                            (
                                f"## Subcategories\n\n{children}\n\n"
                                if has_children
                                else ""
                            ),
                            f'## Pages in category "{category["name"]}"\n\n',
                            f"{pages if has_pages else 'This category has no pages.'}\n\n",
                            self.render_all_categories_link(),
                        ]
                    )
                )

            outfile = File(
                path=str(Path(self.config["base_name"]) / file_name),
                src_dir=str(self.cat_path.parent),
                dest_dir=config["site_dir"],
                use_directory_urls=True,
            )
            files.append(outfile)
        if self.config["generate_index"]:
            files.append(self.generate_index(config))
        return files
