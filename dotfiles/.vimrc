" --- Start with Windows
source ~/.vim/autoload/win.vim
behave mswin
source ~/.vim/autoload/plug.vim

" --- general settings ---
set nocompatible   " Disable vi-compatibility
set guifont=menlo\ for\ powerline:h16
set guioptions-=T " Removes top toolbar
set guioptions-=r " Removes right hand scroll bar
set go-=L " Removes left hand scroll bar
set linespace=15
set t_Co=256

" --- editor settings ---
set showmode                    " always show what mode we're currently editing in
set nowrap                      " don't wrap lines
set tabstop=4                   " a tab is four spaces
set smarttab
set softtabstop=4               " when hitting <BS>, pretend like a tab is removed, even if spaces
set expandtab                   " expand tabs by default (overloadable per file type later)
set shiftwidth=4                " number of spaces to use for autoindenting
set shiftround                  " use multiple of shiftwidth when indenting with '<' and '>'
set backspace=indent,eol,start  " allow backspacing over everything in insert mode
set autoindent                  " always set autoindenting on
set copyindent                  " copy the previous indentation on autoindenting
set number                      " always show line numbers
set ignorecase                  " ignore case when searching
set smartcase                   " ignore case if search pattern is all lowercase,
set mouse=a                     "enable mouse automatically entering visual mode
set ttymouse=xterm2
set clipboard=unnamed,unnamedplus                    "Use system clipboard by default

" --- spell checking ---
set spelllang=en_us         " spell checking
set encoding=utf-8 nobomb   " BOM often causes trouble, UTF-8 is awsum.

" --- performance / buffer ---
set hidden                  " can put buffer to the background without writing
                            "   to disk, will remember history/marks.
set lazyredraw              " don't update the display while executing macros
set ttyfast                 " Send more characters at a given time.

" --- history / file handling ---
set history=999             " Increase history (default = 20)
set undolevels=999          " Moar undo (default=100)
set autoread                " reload files if changed externally

" --- backup and swap files ---
" I save all the time, those are annoying and unnecessary...
set nobackup
set nowritebackup
set noswapfile

" --- search / regexp ---
set gdefault                " RegExp global by default
set magic                   " Enable extended regexes.
set hlsearch                " highlight searches
set incsearch               " show the `best match so far' astyped
set ignorecase smartcase    " make searches case-insensitive, unless they
                            "   contain upper-case letters

" --- UI settings ---
if has('gui_running')
    "set guifont=Menlo:h13
    set gfn:Monaco:h14

    " toolbar and scrollbars
    set guioptions-=T       " remove toolbar
    set guioptions-=L       " left scroll bar
    set guioptions-=r       " right scroll bar
    set guioptions-=b       " bottom scroll bar
    set guioptions-=h      " only calculate bottom scroll size of current line
    set shortmess=atI       " Don't show the intro message at start and
                            "   truncate msgs (avoid press ENTER msgs).
endif

syntax enable
set cursorline
hi CursorLine term=bold cterm=bold guibg=Grey40

set laststatus=2            " Always show status line
set report=0                " Show all changes.
set showcmd                 " show partial command on last line of screen.
set showmatch               " show matching parenthesis
set splitbelow splitright   " how to split new windows.
set title                   " Show the filename in the window title bar.
set scrolloff=5             " Start scrolling n lines before horizontal
                            "   border of window.
set sidescrolloff=7         " Start scrolling n chars before end of screen.
set sidescroll=1            " The minimal number of columns to scroll
                            "   horizontally.

" add useful stuff to title bar (file name, flags, cwd)
" based on @factorylabs
if has('title') && (has('gui_running') || &title)
    set titlestring=
    set titlestring+=%f
    set titlestring+=%h%m%r%w
    set titlestring+=\ -\ %{v:progname}
    set titlestring+=\ -\ %{substitute(getcwd(),\ $HOME,\ '~',\ '')}
endif

" --- command completion ---
set wildmenu                " Hitting TAB in command mode will
set wildchar=<TAB>          "   show possible completions.
set wildmode=list:longest
set wildignore+=*.DS_STORE,*.db,node_modules/**,*.jpg,*.png,*.gif

" --- diff ---
set diffopt=filler          " Add vertical spaces to keep right
                            "   and left aligned.
set diffopt+=iwhite         " Ignore whitespace changes.

" --- folding---
set foldmethod=manual       " manual fold
set foldnestmax=3           " deepest fold is 3 levels
set nofoldenable            " don't fold by default

" --- keys ---
set backspace=indent,eol,start  " allow backspacing over everything.
set esckeys                     " Allow cursor keys in insert mode.
set nostartofline               " Make j/k respect the columns
set timeoutlen=500              " how long it wait for mapped commands
set ttimeoutlen=100             " faster timeout for escape key and others

" Use leader x to remove the current line but not erase buffer
map <leader>x "_dd

" Use leader l to rapidly toggle `set list`
nmap <leader>l :set list!<CR>

" Use a bar-shaped cursor for insert mode, even through tmux.
if exists('$TMUX')
    let &t_SI = "\<Esc>Ptmux;\<Esc>\<Esc>]50;CursorShape=1\x7\<Esc>\\"
    let &t_EI = "\<Esc>Ptmux;\<Esc>\<Esc>]50;CursorShape=0\x7\<Esc>\\"
else
    let &t_SI = "\<Esc>]50;CursorShape=1\x7"
    let &t_EI = "\<Esc>]50;CursorShape=0\x7"
endif

" Ensures that vim moves up/down linewise instead of by wrapped lines
nnoremap j gj
nnoremap k gk

" Easy escaping to normal model
imap jj <esc>

" Open splits
nmap vs :vsplit<cr>
nmap sp :split<cr>

" Allow saving a sudo file if forgot to open as sudo
cmap w!! w !sudo tee % >/dev/null

" turns on nice popup menu for omni completion
:highlight Pmenu ctermbg=238 gui=bold

" --- Leader based key bindings ---
"Auto change directory to match current file ,cd
nnoremap <leader>cd :cd %:p:h<CR>:pwd<CR>
autocmd BufEnter * silent! lcd %:p:h

" Go to tab by number
noremap <leader>1 1gt
noremap <leader>2 2gt
noremap <leader>3 3gt
noremap <leader>4 4gt
noremap <leader>5 5gt
noremap <leader>6 6gt
noremap <leader>7 7gt
noremap <leader>8 8gt
noremap <leader>9 9gt
noremap <leader>0 :tablast<cr>

" Toggle paste mode
nmap <leader>o :set paste!<CR>

" Toggle paste mode
set pastetoggle=<F5>

" Remove trailing whitespace
nnoremap <leader>w :%s/\s\+$//<cr>:let @/=''<CR>

" --- Plugins ---
call plug#begin('~/.vim/plugged')
" Other plugins here.

" Sessions
" Plug 'xolox/vim-session'
" Plug 'xolox/vim-misc'

" Status bar
Plug 'bling/vim-airline'  " Vim status bar
Plug 'vim-airline/vim-airline-themes'
Plug 'ton/vim-bufsurf'

" Git tools
Plug 'airblade/vim-gitgutter'
Plug 'tpope/vim-fugitive' " Git integration
Plug 'junegunn/gv.vim'

" Perforce
Plug 'nfvs/vim-perforce'
Plug 'ngemily/vim-vp4'

" Tools
Plug 'ctrlpvim/ctrlp.vim'
Plug 'scrooloose/nerdtree', { 'on':  'NERDTreeToggle' }
Plug 'Nopik/vim-nerdtree-direnter'  " Fix issue with nerdtree
Plug 'jistr/vim-nerdtree-tabs'
Plug 'scrooloose/nerdcommenter'
Plug 'junegunn/fzf'
Plug 'junegunn/fzf.vim'
" Plug 'fholgado/minibufexpl.vim'  " Buffer explorer
Plug 'yegappan/mru' " MRU
Plug 'tmhedberg/SimpylFold'

" Search
Plug 'jremmen/vim-ripgrep'

" Completion
Plug 'neoclide/coc.nvim', {'for':['zig','cmake','rust',
     \'java','json', 'haskell', 'ts','sh', 'cs',
     \'yaml', 'c', 'cpp', 'd', 'go',
     \'python', 'dart', 'javascript', 'vim'], 'branch': 'release'}

Plug 'Shougo/deoplete.nvim',
Plug 'prabirshrestha/asyncomplete.vim'
Plug 'prabirshrestha/asyncomplete-lsp.vim'
Plug 'lighttiger2505/deoplete-vim-lsp'
Plug 'liuchengxu/vista.vim'
Plug 'prabirshrestha/vim-lsp'
Plug 'mattn/vim-lsp-settings'

" Syntax checker
Plug 'scrooloose/syntastic'  " Adds syntax checking
Plug 'tinyheero/vim-snippets'  " Fork of honza/vim-snippets
Plug 'dense-analysis/ale'

" Tabline
Plug 'ap/vim-buftabline'  " Vim tabs
Plug 'mengelbrecht/lightline-bufferline'
Plug 'itchyny/lightline.vim'

" Python
Plug 'deoplete-plugins/deoplete-jedi',
Plug 'vim-scripts/indentpython.vim'
Plug 'Vimjas/vim-python-pep8-indent'

" C/C++
Plug 'rhysd/vim-clang-format' " Clang-format

" tmux
Plug 'christoomey/vim-tmux-navigator'

" Edition
Plug 'tpope/vim-surround'  " Quoting and parenthesizing made simple
Plug 'tomtom/tcomment_vim'  " Extensible & universal comment
Plug 'Shougo/context_filetype.vim'
Plug 'mbbill/undotree'
Plug 'junegunn/vim-easy-align'
Plug 'godlygeek/tabular'
Plug 'jiangmiao/auto-pairs'
Plug 'alvan/vim-closetag'
Plug 'tpope/vim-surround'
Plug 'tpope/vim-repeat'
Plug 'tpope/vim-capslock'
Plug 'wellle/targets.vim'
Plug 'christoomey/vim-sort-motion'
Plug 'terryma/vim-expand-region'
Plug 'FooSoft/vim-argwrap'
Plug 'gerardbm/vim-md-headings'
Plug 'matze/vim-move'

" Color schemes
Plug 'gerardbm/vim-atomic'
Plug 'rakr/vim-one'
Plug 'sickill/vim-monokai'

call plug#end()

" --- Colors ---
colorscheme monokai
set background=dark

" --- netrw settings ---
nmap <leader>f :Explore<CR>
nmap <leader><s-f> :edit.<CR>

let g:netrw_altv = 1
let g:netrw_dirhistmax = 0

" --- LSP support ---
imap <c-space> <Plug>(asyncomplete_force_refresh)
inoremap <expr> <Tab> pumvisible() ? "\<C-n>" : "\<Tab>"
inoremap <expr> <S-Tab> pumvisible() ? "\<C-p>" : "\<S-Tab>"
inoremap <expr> <cr> pumvisible() ? "\<C-y>\<cr>" : "\<cr>"
autocmd! CompleteDone * if pumvisible() == 0 | pclose | endif

if executable('pyls')
    " pip install python-language-server
    au User lsp_setup call lsp#register_server({
        \ 'name': 'pyls',
        \ 'cmd': {server_info->['pyls']},
        \ 'allowlist': ['python'],
        \ })
endif

let g:vista_executive_for = {
        \ 'cpp': 'vim_lsp',
        \ 'python': 'vim_lsp',
        \ }
let g:vista_ignore_kinds = ['Variable']

let g:coc_disable_startup_warning = 1

" --- Tabbar ---
try
set showtabline=2
set switchbuf=useopen,usetab,newtab
catch
endtry

tab sball
set laststatus=2
nmap <F9> :bprev<CR>
nmap <F10> :bnext<CR>
nmap <silent> <leader>q :SyntasticCheck # <CR> :bp <BAR> bd #<CR>

let g:lightline = {
      \ 'colorscheme': 'one',
      \ 'active': {
      \   'left': [ [ 'mode', 'paste' ], [ 'readonly', 'filename', 'modified' ] ]
      \ },
      \ 'tabline': {
      \   'left': [ ['buffers'] ],
      \   'right': [ ['close'] ]
      \ },
      \ 'component_expand': {
      \   'buffers': 'lightline#bufferline#buffers'
      \ },
      \ 'component_type': {
      \   'buffers': 'tabsel'
      \ }
      \ }

autocmd BufWritePost,TextChanged,TextChangedI * call lightline#update()

let g:lightline#bufferline#show_number  = 1
let g:lightline#bufferline#shorten_path = 0
let g:lightline#bufferline#unnamed      = '[No Name]'

let g:lightline                  = {}
let g:lightline.tabline          = {'left': [['buffers']], 'right': [['close']]}
let g:lightline.component_expand = {'buffers': 'lightline#bufferline#buffers'}
let g:lightline.component_type   = {'buffers': 'tabsel'}

" new tab
map <C-t><C-t> :tabnew<CR>

" close tab
map <C-t><C-x> :tabclose<CR>

" --- Nerd Tree ---
let NERDTreeIgnore=['\.pyc$', '\.pyo$', '__pycache__$']     " Ignore files in NERDTree

map <C-e> :NERDTreeToggle<CR>

" Open files in new tabs in Nerdtree
let NERDTreeMapOpenInTab='\r'

" Toggle NERDTree drawer
map <leader>d <plug>NERDTreeToggle<CR>

" Find files
nnoremap <C-f><C-l> :NERDTreeFind<CR>

" --- Move between buffers ---
map <C-Left> <Esc>:bprev<CR>
map <C-Right> <Esc>:bnext<CR>

map <C-PageUp> :bprevCR>
map <C-PageDown> :bnext<CR>

map <C-P> :bprevCR>
map <C-N> :bnext<CR>

" --- Statusbar ---
let g:airline_theme                       = 'one'
let g:airline_powerline_fonts             = 0
let g:airline#extensions#tabline#enabled  = 1
let g:airline#extensions#tabline#fnamemod = ':t'
let g:airline#extensions#tabline#formatter='unique_tail'
let g:airline_section_z                   = airline#section#create([
            \ '%1p%% ',
            \ 'Ξ%l%',
            \ '\⍿%c'])
call airline#parts#define_accent('mode', 'black')

" --- Default vim file browser :Explore
let g:netrw_liststyle = 3
let g:netrw_banner = 0
let g:netrw_browse_split = 1
let g:netrw_altv = 1
let g:netrw_winsize = 25

" --- Git tools ---
let g:gitgutter_max_signs             = 5000
let g:gitgutter_sign_added            = '+'
let g:gitgutter_sign_modified         = '»'
let g:gitgutter_sign_removed          = '_'
let g:gitgutter_sign_modified_removed = '»╌'
let g:gitgutter_map_keys              = 0
let g:gitgutter_diff_args             = '--ignore-space-at-eol'

nmap <Leader>j <Plug>(GitGutterNextHunk)zz
nmap <Leader>k <Plug>(GitGutterPrevHunk)zz
nnoremap <silent> <C-g> :call <SID>ToggleGGPrev()<CR>zz
nnoremap <Leader>ga :GitGutterStageHunk<CR>
nnoremap <Leader>gu :GitGutterUndoHunk<CR>

" --- Sessions ---
let g:session_autosave  = 'yes'
let g:session_autoload  = 'yes'
let g:session_directory = '~/.vim.cache/sessions'

function! MakeSession(overwrite)
  let b:sessiondir = $HOME . "/.vim.cache/sessions" . getcwd()
  if (filewritable(b:sessiondir) != 2)
    exe 'silent !mkdir -p ' b:sessiondir
    redraw!
  endif
  let b:filename = b:sessiondir . '/session.vim'
  if a:overwrite == 0 && !empty(glob(b:filename))
    return
  endif
  exe "mksession! " . b:filename
endfunction

function! LoadSession()
  let b:sessiondir = $HOME . "/.vim.cache/sessions" . getcwd()
  let b:sessionfile = b:sessiondir . "/session.vim"
  if (filereadable(b:sessionfile))
    exe 'source ' b:sessionfile
  else
    echo "No session loaded."
  endif
endfunction

"Restore cursor to file position in previous editing session
set viminfo='10,\"100,:20,%,n~/.viminfo
au BufReadPost * if line("'\"") > 0|if line("'\"") <= line("$")|exe("norm '\"")|else|exe "norm $"|endif|endif

" Adding automatons for when entering or leaving Vim
if(argc() == 0)
  au VimEnter * nested :call LoadSession()
  au VimLeave * :call MakeSession(1)
else
  au VimLeave * :call MakeSession(0)
endif

" --- CtrlP settings ---
nnoremap <leader>b :CtrlPBuffer<CR>
let g:ctrlp_map                 = '<C-p>'
let g:ctrlp_cmd                 = 'CtrlPBuffer'
let g:ctrlp_working_path_mode   = 'rc'
let g:ctrlp_match_window        = 'bottom,order:btt,min:1,max:10,results:85'
let g:ctrlp_show_hidden         = 1
let g:ctrlp_follow_symlinks     = 1
let g:ctrlp_open_multiple_files = '0i'
let g:ctrlp_prompt_mappings     = {
    \ 'PrtHistory(1)'        : [''],
    \ 'PrtHistory(-1)'       : [''],
    \ 'ToggleType(1)'        : ['<C-l>', '<C-up>'],
    \ 'ToggleType(-1)'       : ['<C-h>', '<C-down>'],
    \ 'PrtCurLeft()'         : ['<C-b>', '<Left>'],
    \ 'PrtCurRight()'        : ['<C-f>', '<Right>'],
    \ 'PrtBS()'              : ['<C-s>', '<BS>'],
    \ 'PrtDelete()'          : ['<C-d>', '<DEL>'],
    \ 'PrtDeleteWord()'      : ['<C-w>'],
    \ 'PrtClear()'           : ['<C-u>'],
    \ 'ToggleByFname()'      : ['<C-g>'],
    \ 'AcceptSelection("e")' : ['<C-m>', '<CR>'],
    \ 'AcceptSelection("h")' : ['<C-x>'],
    \ 'AcceptSelection("t")' : ['<C-t>'],
    \ 'AcceptSelection("v")' : ['<C-v>'],
    \ 'OpenMulti()'          : ['<C-o>'],
    \ 'MarkToOpen()'         : ['<c-z>'],
    \ 'PrtExit()'            : ['<esc>', '<c-c>', '<c-p>'],
    \ }

" Ignore some files when fuzzy searching
let g:ctrlp_custom_ignore = {
  \ 'dir':  '\v[\/]\.?(git|hg|svn|meteor|bundle|node_modules|bower_components)$',
  \ 'file': '\v\.(so|swp|zip)$'
  \ }

" --- Undotree toggle ---
nnoremap <Leader>u :UndotreeToggle<CR>

" --- Multiple windows ---
" Remap wincmd
map <Leader>, <C-w>

set winminheight=0
set winminwidth=0
set splitbelow
set splitright
set fillchars+=stlnc:\/,vert:│,fold:―,diff:―

" Split windows
map <C-w>- :split<CR>
map <C-w>. :vsplit<CR>
map <C-w>x :close<CR>
map <C-w>q :q!<CR>
map <C-w>, <C-w>=

" Resize windows
if bufwinnr(1)
    map + :resize +1<CR>
    map - :resize -1<CR>
    map < :vertical resize +1<CR>
    map > :vertical resize -1<CR>
endif

" Toggle resize window
nnoremap <silent> <C-w>f :call <SID>ToggleResize()<CR>

" Last, previous and next window; and only one window
nnoremap <silent> <C-w>l :wincmd p<CR>:echo "Last window."<CR>
nnoremap <silent> <C-w>p :wincmd w<CR>:echo "Previous window."<CR>
nnoremap <silent> <C-w>n :wincmd W<CR>:echo "Next window."<CR>
nnoremap <silent> <C-w>o :wincmd o<CR>:echo "Only one window."<CR>

" setting horizontal and vertical splits
set splitbelow
set splitright

" split navigations
nnoremap <C-J> <C-W><C-J>
nnoremap <C-K> <C-W><C-K>
nnoremap <C-L> <C-W><C-L>
nnoremap <C-H> <C-W><C-H>

"  --- Folding ---
" Enable folding
set foldmethod=indent
set foldlevel=99

" Enable folding with the spacebar
nnoremap <space> za

" --- NERDCommenter settings ---
let g:NERDDefaultAlign          = 'left'
let g:NERDSpaceDelims           = 1
let g:NERDCompactSexyComs       = 1
let g:NERDCommentEmptyLines     = 0
let g:NERDCreateDefaultMappings = 0
let g:NERDCustomDelimiters      = {
    \ 'python': {'left': '#'},
    \ }

nnoremap cc :call NERDComment(0,'toggle')<CR>
vnoremap cc :call NERDComment(0,'toggle')<CR>

" --- FZF settings ---
let $FZF_PREVIEW_COMMAND = 'cat {}'
nnoremap <C-f><C-f> :Files<CR>
nnoremap <C-f><C-g> :Commits<CR>
nnoremap <C-f><Space> :BLines<CR>

" --- ALE settings ---
let g:ale_sign_column_always = 1
let g:ale_linters            = {
    \ 'c'          : ['clang'],
    \ 'python'     : ['pylint'],
    \ 'javascript' : ['jshint'],
    \ 'css'        : ['csslint'],
    \ 'tex'        : ['chktex'],
    \ }

" --- Syntastic settings ---
set statusline+=%#warningmsg#
set statusline+=%{SyntasticStatuslineFlag()}
set statusline+=%*

let g:syntastic_always_populate_loc_list=1
let g:syntastic_auto_loc_list=1
let g:syntastic_enable_signs=1
let g:syntastic_aggregate_errors=1
let g:syntastic_loc_list_height=5
let g:syntastic_error_symbol='X'
let g:syntastic_style_error_symbol='X'
let g:syntastic_warning_symbol='x'
let g:syntastic_style_warning_symbol='x'
let g:syntastic_python_checkers=['flake8', 'pydocstyle', 'python3']

let g:syntastic_check_on_open = 0
let g:syntastic_check_on_wq = 1

" --- Setting up indendation ---
au BufNewFile, BufRead *.py
    \ set tabstop=4 |
    \ set softtabstop=4 |
    \ set shiftwidth=4 |
    \ set textwidth=79 |
    \ set expandtab |
    \ set autoindent |
    \ set fileformat=unix

au BufNewFile, BufRead *.js, *.html, *.css
    \ set tabstop=2 |
    \ set softtabstop=2 |
    \ set shiftwidth=2
