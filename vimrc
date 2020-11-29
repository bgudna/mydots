set expandtab
set tabstop=4
"set laststatus=2
set softtabstop=4
set shiftwidth=4
set nu
set autoindent
set textwidth=80
set mouse=a
set noswapfile


" vundle 
filetype off
set nocompatible
set rtp+=~/.vim/bundle/Vundle.vim
call vundle#begin()
" vundle plugins
Plugin 'VundleVim/Vundle.vim'
Plugin 'scrooloose/nerdtree'
Plugin 'morhetz/gruvbox'
Plugin 'vim-airline/vim-airline'
" Plugin 'godlygeek/tabular'
" Plugin 'plasticboy/vim-markdown'
call vundle#end()
filetype plugin indent on

colorscheme gruvbox
set background=dark
let g:airline#extensions#tabline#enabled = 1
let g:airline#extensions#tabline#fnamemod = ':t'

"opna nerdtree
map <C-h> :NERDTreeToggle<CR>

"statuslinu options
set laststatus=2
set statusline=
set statusline+=%2*\ %l
set statusline+=\ %*
set statusline+=%1*\ ‹‹
set statusline+=%1*\ %f\ %*
set statusline+=%1*\ ››
set statusline+=%1*\ %m
set statusline+=%3*\ %F
set statusline+=%=
"set statusline+=%3*\ %{LinterStatus()}
set statusline+=%3*\ ‹‹
set statusline+=%3*\ %{strftime('%R',getftime(expand('%')))}
set statusline+=%3*\ ::
set statusline+=%3*\ %n
set statusline+=%3*\ ››\ %*
hi User1 guifg=#FFFFFF guibg=#191f26 gui=BOLD
hi User2 guifg=#000000 guibg=#959ca6
hi User3 guifg=#000000 guibg=#4cbf99
