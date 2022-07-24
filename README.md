# Doc Comments

- [Introduction](#introduction)
- [Usage & Configuration](#usage)
- [Installation](#installation)
- [Contributing](#contributing)

## <a id="introduction"></a>Introduction

This plugin aims to bring GoogleDocs-style comments to Neovim.

![demo](./demo.gif)

This plugin has been tested on Neovim 0.7.0 and may not work on earlier versions. It will not work in Vim.

## <a id="usage"></a>Usage & Configuration

This plugin defines five commands:

- `MakeCommentVisual`, which creates a comment on a visual mode selection;
- `MakeCommentNormal`, which creates a comment on a motion or text object (ex. `:MakeCommentNormal<cr>iw` comments the "inner word" text object);
- `GetComment`, which displays the comment under or before the cursor as a tooltip;
- `EditComment`, which displays the comment under or before the cursor in a floating window and allows edits;
- `DeleteComment`, which deletes the comment under or before the cursor.

Example mappings:

```
vnoremap c :MakeCommentVisual<cr>
nnoremap yc :MakeCommentNormal<cr>
nnoremap <leader>dc :DeleteComment<cr>
nnoremap K :GetComment<cr>
nnoremap <leader>ec :EditComment<cr>
```

This plugin does not remap any keys by default.

Doc Comments uses the following variables for customization:

- `g:DocCommentsHighlightGroup`, the highlight group for commented text (defaults to "Underlined");
- `g:DocCommentsEditWindowHeight`, the height of the `EditComment` window (defaults to 10);
- `g:DocCommentsEditWindowWidth`, the width of the `EditComment` window (defaults to 55);
- `g:DocCommentsPreviewWidth`, the max width of the `GetComment` window (defaults to 50. Height will change to accomodate the text);
- `g:DocCommentsPath`, the path to store/look for comment files. By default, comment files will be stored in the same directory as the original file. Comment files are named according to the convention `.[name of original file]_comments`.

## <a id="installation"></a>Installation

Install manually or use Vim-Plug:

```
Plug 'oxytocin/DocComments', { 'do': 'UpdateRemotePlugins' } 
```

Other plugin managers will probably also work, but remember to run `UpdateRemotePlugins` after installing.

Requires the Python package `Neovim`:

```
pip install neovim
```

## <a id="contributing"></a>Contributing

Open to suggestions; this is my first vim plugin, so I am sure there is room for improvement. Please submit issues for bugs. Pull requests are welcome.
