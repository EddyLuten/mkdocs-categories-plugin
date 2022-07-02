"""mkdocs-categories-plugin

An MkDocs plugin allowing for categorization of pages in your wiki.
"""

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


def get_page_title(page_src: str, meta_data: dict) -> str:
    """Returns the title of the page. The title in the meta data section
    will take precedence over the H1 markdown title if both are provided."""
    return str(
        meta_data['title']
        if 'title' in meta_data and isinstance(meta_data['title'], str)
        else get_markdown_title(page_src) or ''
    )

def slugify(title: str) -> str:
    """Returns the path slug used for the category URL.
    Adapted from django.utils.text"""
    slug = unicodedata.normalize('NFKD', str(title)).encode('ascii', 'ignore').decode('ascii')
    slug = re.sub(r'[^\w\s-]', '', slug).strip().lower()
    return re.sub(r'[-\s]+', '-', slug)

class CategoriesPlugin(BasePlugin):
    """
    Defines the exported MkDocs plugin class and all its functionality.
    """
    config_scheme = (
        ('generate_index', config_options.Type(bool, default=True)),
        ('verbose', config_options.Type(bool, default=False)),
        ('no_nav', config_options.Type(bool, default=False)),
        ('base_name', config_options.Type(str, default='categories')),
        ('section_title', config_options.Type(str, default='Categories'))
    )
    log: Logger = getLogger(f'mkdocs.plugins.{__name__}')
    categories: dict = {}
    pages:dict = {}
    cat_path: Path = Path()

    def on_config(self, _):
        """Set the log level if the verbose config option is set"""
        self.log.setLevel(
            logging.INFO if self.config['verbose'] else logging.WARNING
        )
        self.cat_path = Path(self.config['base_name'])
        if self.cat_path.exists():
            self.clean_temp_dir()
        self.cat_path.mkdir(parents=True)

    def clean_temp_dir(self):
        """Remove the temporary directory after execution."""
        shutil.rmtree(self.cat_path)

    def on_nav(self, nav, **_):
        """
        Executed when the navigation is created. If the config option no_nav
        is set to true, the categories section will be removed from the global
        navigation.
        """
        if not self.config['no_nav']:
            return nav
        for item in nav:
            if item.is_section and str(item.title).lower() == self.config['base_name']:
                nav.items.remove(item)
                break
        return nav

    def on_build_error(self, **_):
        """Executed after the build has failed."""
        self.categories.clear()
        self.clean_temp_dir()

    def on_post_build(self, **_):
        """Executed after the build has successfully completed."""
        self.log.info("Defined %s categories.", len(self.categories))
        self.categories.clear()
        self.clean_temp_dir()

    def on_page_markdown(self, markdown: str, page: Page, **_):
        """Appends the category links section for a page to the markdown."""
        relative_url = get_relative_url(str(self.cat_path), page.file.url)
        if page.file.url not in self.pages:
            return markdown
        links = list(map(
            lambda c: f"- [{c}]({relative_url}/{self.categories[c]['slug']}/)",
            sorted(self.pages[page.file.url])
        ))
        return (
            markdown +
            f"\n## {self.config['section_title']}\n\n" +
            "\n".join(links)
        )

    def add_category(self, cat_name: str) -> None:
        """Register a category if it does not yet exist."""
        if cat_name in self.categories:
            return
        slugified = slugify(cat_name)
        self.categories[cat_name] = {
            'name':  cat_name,
            'slug':  slugified,
            'pages': []
        }
        self.log.info('Defined new category "%s" with slug "%s"', cat_name, slugified)

    def register_page(self, cat_name: str, page_url: str, page_title: str) -> None:
        """Register a page and, if it does not exist, its category."""
        # Each category stores which pages belong to it
        self.add_category(cat_name)
        self.categories[cat_name]['pages'].append({
            'title': page_title,
            'url':   f"{page_url}{'' if page_url.endswith('/') else '/'}"
        })

        # Each page also stores which categories it belongs to
        if page_url not in self.pages:
            self.pages[page_url] = set()
        self.pages[page_url].add(cat_name)

    def define_categories(self, files) -> None:
        """Read all of the meta data and define any categories."""
        for file in filter(lambda f: f.is_documentation_page(), files):
            with open(file.abs_src_path, encoding='utf-8') as handle:
                source, meta_data = meta.get_data(handle.read())
                if len(meta_data) <= 0 or 'categories' not in meta_data:
                    continue
                if not isinstance(meta_data['categories'], list):
                    self.log.error(
                        'The categories object at %s was not a list, but %s',
                        str(file.url),
                        type(meta_data['categories'].__name__)
                    )
                    continue
                for category in meta_data['categories']:
                    self.register_page(
                        str(category),
                        str(file.url),
                        get_page_title(source, meta_data)
                    )

    def generate_index(self, config) -> File:
        """Generates a categories index page if the option is set."""
        joined = "\n".join(map(
            lambda c: f"- [{c['name']}]({str(c['slug'])}/) ({len(c['pages'])})",
            sorted(self.categories.values(), key=lambda c: c['name'])
        ))
        with open(self.cat_path / 'index.md', mode="w", encoding='utf-8') as file:
            file.write(
                "# All Categories\n\n"
                "\n"
                f"There are a total of {len(self.categories.keys())} categories(s):\n"
                "\n"
                f"{joined}\n"
            )
        return File(
            path               = str(self.cat_path / 'index.md'),
            src_dir            = str(self.cat_path.parent),
            dest_dir           = config['site_dir'],
            use_directory_urls = True
        )

    def all_categories_link(self) -> str:
        """Generates a link to the categories index page if the option is set"""
        return (
            '' if not self.config['generate_index']
            else "[All Categories](../)\n\n"
        )

    def on_files(self, files, config, **_):
        """When MkDocs loads its files, load any defined categories."""
        self.define_categories(files)
        for category in self.categories.values():
            joined = "\n".join(map(
                lambda p: f"- [{p['title']}](../../{p['url']})",
                sorted(category['pages'], key=lambda p: p['title'])
            ))

            file_name = f"{category['slug']}.md"
            with open(self.cat_path / file_name, mode="w", encoding='utf-8') as file:
                file.write(
                    f"# {category['name']}\n"
                    "\n"
                    + self.all_categories_link() +
                    f"This category contains {len(category['pages'])} page(s):\n"
                    "\n"
                    f"{joined}\n"
                )

            outfile = File(
                path               = str(Path(self.config['base_name']) / file_name),
                src_dir            = str(self.cat_path.parent),
                dest_dir           = config['site_dir'],
                use_directory_urls = True
            )
            files.append(outfile)
        if self.config['generate_index']:
            files.append(self.generate_index(config))
        return files
