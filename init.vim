" Options
set background=dark
set clipboard=unnamedplus
set completeopt=noinsert,menuone,noselect
set cursorline
set hidden
set inccommand=split
set mouse=a
set number
set relativenumber
set splitbelow splitright
set title
set ttimeoutlen=0
set wildmenu

" Tabs size
 set expandtab
 set shiftwidth=2
 set tabstop=2

 filetype plugin indent on
 syntax on

 set t_Co=256

 call plug#begin()
 " Appearance
    Plug 'vim-airline/vim-airline'
    Plug 'ryanoasis/vim-devicons'
    Plug 'morhetz/gruvbox'

call plug#end()

colorscheme gruvbox
