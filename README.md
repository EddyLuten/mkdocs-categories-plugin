# mkdocs-categories-plugin

[![PyPI version](https://badge.fury.io/py/mkdocs-categories-plugin.svg)](https://pypi.org/project/mkdocs-categories-plugin/)  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) ![example workflow](https://github.com/eddyluten/mkdocs-categories-plugin/actions/workflows/pylint.yml/badge.svg) [![Downloads](https://pepy.tech/badge/mkdocs-categories-plugin)](https://pepy.tech/project/mkdocs-categories-plugin)

An MkDocs plugin allowing for categorization of pages in your wiki. This plugin allows for multiple categories per page and will generate a category index page with links to each page within the category.

If you like this MkDocs plugin, you'll probably also like [mkdocs-alias-plugin](https://github.com/EddyLuten/mkdocs-alias-plugin) and [mkdocs-live-edit-plugin](https://github.com/EddyLuten/mkdocs-live-edit-plugin).

## Installation

Using Python 3.10 or greater, install the package using pip:

```zsh
pip install mkdocs-categories-plugin
```

Then add the following entry to the plugins section of your `mkdocs.yml` file:

```yml
plugins:
  - categories
```

**Important:** If you already have a directory named `categories` in your project's root directory or a section named `categories`, you must change the `base_name` option to something else in order to prevent issues or data loss.

For further configuration, see the Options section below.

## Usage

Add a `categories` section to your page's meta block:

```yaml
---
categories:
    - Novels
    - Fiction
    - 19th Century Gothic Fiction
---
```

New pages will be generated for each of these categories, with a list of links to each of the wiki pages within the category. Subcategories, links to the parent category, and a link to the "All Categories" page are automatically generated and placed on the page.

Category names are slugified before used in category URLs. For example, `19th Century Gothic Fiction` becomes `19th-century-gothic-fiction`.

Please refer to the [MkDocs documentation](https://www.mkdocs.org/user-guide/writing-your-docs/#yaml-style-meta-data) for more information on how the meta-data block is used.

### Subcategories

As of version 0.3.0, mkdocs-categories-plugin supports subcategorization. This is achieved by supplying a category name that separates parent from child categories using a separator (by default `|`, configurable via `category_separator`). You may supply as many levels of child categories as you like.

For example:

```yaml
categories:
    - Fiction|Romance
    - Fiction|Books|British Authors|Female|19th Century
```

The first category definition in this example places the page in the *Romance* subcategory of the *Fiction* parent category. Note that the page will **not** be placed in the parent category of *Fiction*, but only in the *Romance* category. The second category definition places the page in the *19th Century* category, but not in any of its ancestor categories.

## Options

You may customize the plugin by passing options into the plugin's configuration sections in `mkdocs.yml`:

```yaml
plugins:
    - categories:
        generate_index: true
        verbose: false
        base_name: 'categories'
        section_title: 'Categories'
        no_nav: false
        category_separator: '|'
```

### `generate_index`

**Default:** `true`

If true, an index page listing all of the generated categories is created at the `base_name` URL.

### `verbose`

**Default:** `false`

You may use the optional `verbose` option to print more information about which categories were defined during build and how many in total.

### `base_name`

**Default:** `categories`

A string that's used to both serve as the URL base for the category pages as well as the navigation section that's automatically generated. Since this string is used in the generated category URL, please ensure that it only contains URL-friendly characters.

### `section_title`

**Default:** `Categories`

This is the string that's used to render the H2 header at the bottom of each page that defines categories. It is followed by a list of links to each category.

### `no_nav`

**Default:** `false`

By default, mkdocs-categories-plugin will generate navigation entries for each category page under the `base_name` that you provided. If you want to turn this behavior off, set this option to `true`.

There's also a know issue with mkdocs-awesome-pages-plugin compatibility that does not allow you to reorder the position of the generated categories section by using a `.pages` file. If you would rather turn the navigation entries off entirely, this option is for you.

### `category_separator`

**Default:** `|`

This string is used to split the category name in order to define a category hierarchy (see subcategories above).

## Troubleshooting

### There's a directory named `categories` in my project

A fatal error must have occurred during the compilation of your site and left the temporary directory containing the intermediate markdown files used by this plugin behind. It is safe to delete this directory since it's only used during the build.

### `The categories object at URL was not a list, but TYPE`

The page identified did not contain a valid categories configuration object. Please make sure that this is an array of strings.

## Changelog

### 0.5.0

Fixes many build info warnings about absolute paths due to MkDocs' improved validation. Made the links that are generated more correct.

### 0.4.0

Fixes sorting categories, child pages, etc. containing numbers by using natural sorting from the `natsort` package rather than the default sorting function.

### 0.3.0

Added support for subcategories. Python 3.10 or higher is now required.

### 0.2.1

Patch release: implements a bug fix by @rpmzandwijk reported in [#1](https://github.com/EddyLuten/mkdocs-categories-plugin/issues/1).

### 0.2.0

Introduces support for the automatic generation of category index pages. This new default behavior can be turned off using an option.

### 0.1.1

Fixed a breaking bug caused by passing the wrong data into `sorted`.

### 0.1.0

Initial release with all of the base logic in place.
