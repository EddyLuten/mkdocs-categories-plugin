"""mkdocs-categories-plugin

An MkDocs plugin allowing for categorization of pages in your wiki.
"""

import shutil
import re
import logging
import unicodedata
from pathlib import Path
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File
from mkdocs.utils import meta, get_markdown_title
from mkdocs.config import config_options

def get_page_title(page_src, meta_data):
    """Returns the title of the page. The title in the meta data section
    will take precedence over the H1 markdown title if both are provided."""
    return (
        meta_data['title']
        if 'title' in meta_data and isinstance(meta_data['title'], str)
        else get_markdown_title(page_src)
    )

def slugify(title):
    """Returns the path slug used for the category URL.
    Adapted from django.utils.text"""
    slug = unicodedata.normalize('NFKD', str(title)).encode('ascii', 'ignore').decode('ascii')
    slug = re.sub(r'[^\w\s-]', '', slug).strip().lower()
    return re.sub(r'[-\s]+', '-', slug)

class CategoriesPlugin(BasePlugin):
    """
    TODO
    """
    config_scheme = (
        ('verbose', config_options.Type(bool, default=False)),
        ('no_nav', config_options.Type(bool, default=False)),
        ('base_name', config_options.Type(str, default='categories')),
        ('section_title', config_options.Type(str, default='Categories'))
    )
    categories = {}
    pages = {}
    log = logging.getLogger(f'mkdocs.plugins.{__name__}')
    cat_path = Path()

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

    def on_page_markdown(self, markdown, page, **_):
        """Replaces any alias tags on the page with markdown links."""
        if page.file.url not in self.pages:
            return markdown
        links = list(map(
            lambda c: f"- [{c}](/{self.cat_path / self.categories[c]['slug']})",
            sorted(self.pages[page.file.url])
        ))
        return (
            markdown +
            f"\n## {self.config['section_title']}\n\n" +
            "\n".join(links)
        )

    def add_category(self, cat_name):
        """Register a category if it does not yet exist."""
        if cat_name in self.categories:
            return
        slugified = slugify(cat_name)
        self.categories[cat_name] = {
            'name': cat_name,
            'slug': slugified,
            'pages': []
        }
        self.log.info('Defined new category "%s" with slug "%s"', cat_name, slugified)

    def register_page(self, cat_name, page_url, page_title):
        """Register a page and, if it does not exist, its category."""
        # Each category stores which pages belong to it
        self.add_category(cat_name)
        self.categories[cat_name]['pages'].append({
            'title': page_title,
            'url': page_url
        })

        # Each page also stores which categories it belongs to
        if page_url not in self.pages:
            self.pages[page_url] = set()
        self.pages[page_url].add(cat_name)

    def define_categories(self, files):
        """Read all of the meta data and define any categories."""
        for file in filter(lambda f: f.is_documentation_page(), files):
            with open(file.abs_src_path, encoding='utf-8') as handle:
                source, meta_data = meta.get_data(handle.read())
                if len(meta_data) <= 0 or 'categories' not in meta_data:
                    continue
                if not isinstance(meta_data['categories'], list):
                    self.log.error(
                        'The categories object at %s was not a list, but %s',
                        file.url,
                        type(meta_data['categories'].__name__)
                    )
                    continue
                for category in meta_data['categories']:
                    self.register_page(
                        category,
                        file.url,
                        get_page_title(source, meta_data)
                    )

    def on_files(self, files, config, **_):
        """When MkDocs loads its files, load any defined categories."""
        self.define_categories(files)
        for category in self.categories.values():
            joined = "\n".join(map(
                lambda p: f"- [{p['title']}](/{p['url']})",
                sorted(category['pages'], key=lambda p: p['title'])
            ))

            file_name = f"{category['slug']}.md"
            with open(self.cat_path / file_name, mode="w", encoding='utf-8') as file:
                file.write(
                    f"# {category['name']}\n"
                    "\n"
                    f"This category contains {len(category['pages'])} page(s):\n"
                    "\n"
                    f"{joined}\n"
                )

            outfile = File(
                path = str(Path(self.config['base_name']) / file_name),
                src_dir = str(self.cat_path.parent),
                dest_dir = config['site_dir'],
                use_directory_urls = True
            )
            files.append(outfile)
        return files
