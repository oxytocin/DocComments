"Even if the user doesn't want to show comments, we need to load the extmarks so changes in position can be tracked. Then next time they do enable comments, if won't be borked.
"We check the filetype on autocmds first to avoid annoying errors when starting vim on a netrw buffer
autocmd VimEnter * if &ft!="netrw" | exec "LoadComments" | endif
autocmd BufWritePre * if &ft!="netrw" | exec "UpdateMarkLocations" | endif
autocmd BufAdd * if &ft!="netrw" | exec "LoadComments" | endif
