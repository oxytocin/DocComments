"if user modifies text before extmarks are placed, it messes up their placement, so we diable modifications
"on startup if a comment file is present. The __init__ method in DocComments.py re-enables modifications once extmarks are placed.
let comment_file_head = expand("%:p:h")
let comment_file_tail = expand("%:p:t")
let full = comment_file_head . "/." . comment_file_tail . "_comments"
if filereadable(full)
    set nomodifiable
endif
"Even if the user doesn't want to show comments, we need to load the extmarks so changes in position can be tracked.
"We check the filetype on autocmds first to avoid annoying errors when starting vim on a netrw buffer
autocmd VimEnter * if &ft!="netrw" | exec "LoadComments" | endif
autocmd BufWritePre * if &ft!="netrw" | exec "UpdateMarkLocations" | endif
autocmd BufAdd * if &ft!="netrw" | exec "LoadComments" | endif
