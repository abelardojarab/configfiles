# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

# If not running interactively, don't do anything
[ -z "$PS1" ] && return

# tells Readline to perform filename completion in a case-insensitive fashion
bind "set completion-ignore-case on"

# filename matching during completion will treat hyphens and underscores as equivalent
bind "set completion-map-case on"

# will get Readline to display all possible matches for an ambiguous pattern at the first <Tab> press instead of at the second
bind "set show-all-if-ambiguous on"

# don't put duplicate lines or lines starting with space in the history.
# See bash(1) for more options
export HISTCONTROL=ignoreboth
export HISTIGNORE="&:ls:[bf]g:[cb]d:b:history:exit:[ ]*"

# append to the history file, don't overwrite it
shopt -s histappend

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
export HISTSIZE=50000
export HISTFILESIZE=50000

# useful timestamp format
MY_BASH_BLUE="\033[0;34m" #Blue
MY_BASH_NOCOLOR="\033[0m"
export HISTTIMEFORMAT=`echo -e ${MY_BASH_BLUE}[%F %T] $MY_BASH_NOCOLOR `

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    export LS_COLORS='di=34:ln=36:so=0:pi=0:ex=32:bd=0:cd=0:su=0:sg=0:tw=34:ow=34:'
    alias ls='ls --color=auto'
    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi

# some more ls aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

# Use gpg2
alias gpg='gpg2'

# rsync utilities
alias rsynccopy="rsync --partial --progress --append --rsh=ssh -r -h "
alias rsyncmove="rsync --partial --progress --append --rsh=ssh -r -h --remove-sent-files"

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

# Alias definitions.
# You may want to put all your additions into a separate file like
# ~/.bash_aliases, instead of adding them here directly.
# See /usr/share/doc/bash-doc/examples in the bash-doc package.

if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if [ -f /etc/bash_completion ] && ! shopt -oq posix; then
    . /etc/bash_completion
fi

# Custom installs directory
SW=$HOME/sw

# NVIDIA settings
export GPU_FORCE_64BIT_PTR=0
export GPU_MAX_HEAP_SIZE=100
export GPU_USE_SYNC_OBJECTS=1
export GPU_MAX_ALLOC_PERCENT=95
export GPU_SINGLE_ALLOC_PERCENT=100

# Editor setup
export VISUAL=vim
export EDITOR="$VISUAL"

# Emacs settings
export EMACS_SERVER_FILE=$HOME/.emacs.cache/server/server
export PATH=$HOME/.cask/bin:$PATH

# Flexlm settings
export theHost=`hostname`
alias lmlicense='/opt/mentor/calibre/2013.3_28.19/bin/lmgrd -c'

# Python settings
export PYTHONPATH=${PYTHONPATH}:/usr/local/lib/python2.7/dist-packages:/usr/lib/python2.7/dist-packages:~/workspace/pythonlibs/lib/python2.7/dist-packages
export PYTHONPATH=${PYTHONPATH}:/usr/local/lib/python2.7/site-packages:/usr/lib/python2.7/site-packages
export PYTHONPATH=${PYTHONPATH}:/opt/oaScript/python2

# Java options
export JAVA_HOME=/usr/lib/jvm/java-9-oracle

# OpenAccess
export OA_UNSUPPORTED_PLAT=linux_rhel50_gcc44x
export OA_HOME=/opt/cadence/installs/IC616/oa_v22.43.018

# PDKs
export CDK_DIR=/opt/ncsu-cdk-1.6.0
export PDK_DIR=/opt/FreePDK45
export PDK_DIR_SC=/opt/FreePDK45StandardCells

# Cadence settings
export CDS_AUTO_64BIT=NONE
export CDSROOT=/opt/cadence/installs/IC615
export CDSHOME=/opt/cadence/installs/IC615
export CDS_ROOT=/opt/cadence/installs/IC615
export BASIC_LIB_PATH=$CDSROOT/tools/dfII/etc/cdslib/basic
export ANALOG_LIB_PATH=$CDSROOT/tools/dfII/etc/cdslib/artist/analogLib/
export CDS_LIC_FILE=27000@ubuntu
export CDS_LOG_PATH=/tmp
export CDS_LOG_VERSION=pid
export CDS_AUTO_CKOUT=all
export CDS_LOAD_ENV=CWD
export CDS_Netlisting_Mode=Analog
export EDI_ROOT=/opt/cadence/installs/EDI131
export MMSIM_ROOT=/opt/cadence/installs/MMSIM121
export PATH=$MMSIM_ROOT/tools/bin:$MMSIM_ROOT/tools/spectre/bin:$CDS_ROOT/tools/bin:$CDS_ROOT/tools/dfII/bin:$PATH:$EDI_ROOT/bin
export LM_LICENSE_FILE=$HOME/flexlm/cadence.dat

# Apache settings
export APACHEDA_LICENSE_FILE=$HOME/flexlm/apache.dat
export APACHEROOT=/opt/ansys/Totem14.1.b2
export PATH=$APACHEROOT/bin:$PATH
export LM_LICENSE_FILE=$LM_LICENSE_FILE:$HOME/flexlm/apache.dat

# Synopsys settings
export SYNOPSYS=/opt/synopsys
export SNPSLMD_LICENSE_FILE=$HOME/flexlm/synopsys.dat
export SNPS_DC_ROOT=/opt/synopsys/designcompiler/B-2008.09
export SNPS_HSPICE_ROOT=/opt/synopsys/hspice/F-2011.09-SP2
export SNPS_STARRC_ROOT=/opt/synopsys/starrc/H-2012.12
export SNPS_COSMOSSCOPE_ROOT=/opt/synopsys/cosmosscope/H-2012.12
export SNPS_ICWB_ROOT=/opt/synopsys/icweb/G-2012.06-SP1
export SNPS_ICV_ROOT=/opt/synopsys/icvalidator/H-2013.06
export PATH=$SNPS_HSPICE_ROOT/hspice/linux:$SNPS_DC_ROOT/bin:$SNPS_STARRC_ROOT/bin:$SNPS_COSMOSSCOPE_ROOT/ai_bin:$PATH
export PATH=$SNPS_ICWB_ROOT/bin/amd64:$SNPS_ICV_ROOT/bin/SUSE.64:$PATH
export LM_LICENSE_FILE=$LM_LICENSE_FILE:$HOME/flexlm/synopsys.dat

# Calibre settings
export CALIBRE_HOME=/opt/mentor/calibre/2013.3_28.19
export MGC_HOME=/opt/mentor/calibre/2013.3_28.19
export PATH=$CALIBRE_HOME/bin:$PATH
export MGLS_LICENSE_FILE=$HOME/flexlm/calibre.dat
export LM_LICENSE_FILE=$LM_LICENSE_FILE:$HOME/flexlm/calibre.dat

# Modelsim settings
export MTI_HOME=/opt/mentor/modelsim/10.5a/modeltech
export PATH=$MTI_HOME/bin:$PATH
export LM_LICENSE_FILE=$HOME/flexlm/modelsim.dat:$LM_LICENSE_FILE:
export MGLS_LICENSE_FILE=$HOME/flexlm/modelsim.dat:$MGLS_LICENSE_FILE
export MTI_VCO_MODE=64
export COMP64=1

# Aldec settings
export ALDEC_LICENSE_FILE=$HOME/flexlm/aldec.dat

# Matlab settings
export PATH=/opt/MATLAB/R2012b/bin:$PATH
export LM_LICENSE_FILE=$LM_LICENSE_FILE:$HOME/flexlm/matlab.dat

# Altera settings
export QUARTUS_ROOT=/opt/intelFPGA_pro/17.1
export QUARTUS_HOME=$QUARTUS_ROOT/quartus
export PATH=$QUARTUS_ROOT/quartus/bin:$PATH
export ALTERAOCLSDKROOT=$QUARTUS_ROOT/hld
export QSYS_ROOTDIR=$QUARTUS_ROOT/quartus/sopc_builder/bin
export LM_LICENSE_FILE=1800@ubuntu01:1900@ubuntu01:$LM_LICENSE_FILE:$HOME/flexlm/altera.dat

# Xilinx settings
export PATH=$PATH:/opt/Xilinx/14.7/ISE_DS/ISE/bin/lin64
export LM_LICENSE_FILE=$LM_LICENSE_FILE:$HOME/flexlm/Xilinx.lic

# SPSS settings
export PATH=/opt/IBM/SPSS/Statistics/22/bin:$PATH

# Sublime Text settings
export PATH=/opt/sublime_text:$PATH

# Master PDF 3 and PDF Studio
export PATH=/opt/master-pdf-editor-3:$PATH
export PATH=/opt/PDFStudio:$PATH

# JetBrains tools
export PATH=/opt/JetBrains/clion-2017.2.2/bin:$PATH
export PATH=/opt/JetBrains/pycharm-2017.2.3/bin:$PATH
export PATH=/opt/JetBrains/WebStorm-172.4155.35/bin:$PATH
export PATH=/opt/JetBrains/license_server:$PATH
alias jblicense='/opt/JetBrains/license_server/jb_licsrv.linux.amd64'

# Set up general GTAGS location
export GTAGSLIBPATH=$HOME/.gtags/
export GTAGSTHROUGH=true
export GTAGSLABEL=exuberant-ctags

# Perl options (needed by Verilator)
PATH="${HOME}/perl5/bin${PATH:+:${PATH}}"; export PATH;
PERL5LIB="${HOME}/perl5/lib/perl5${PERL5LIB:+:${PERL5LIB}}"; export PERL5LIB;
PERL_LOCAL_LIB_ROOT="${HOME}/perl5${PERL_LOCAL_LIB_ROOT:+:${PERL_LOCAL_LIB_ROOT}}"; export PERL_LOCAL_LIB_ROOT;
PERL_MB_OPT="--install_base \"${HOME}/perl5\""; export PERL_MB_OPT;
PERL_MM_OPT="INSTALL_BASE=${HOME}/perl5"; export PERL_MM_OPT;

# Hadoop dev
if [ -e ~/.hadoop/HADOOP_HOME ]; then
    export HADOOP_HOME=$HOME/.hadoop/HADOOP_HOME

    # Extra directories
    export HADOOP_COMMON_HOME=$HADOOP_HOME
    export HADOOP_HDFS_HOME=$HADOOP_HOME
    export HADOOP_MAPRED_HOME=$HADOOP_HOME
    export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
    export YARN_HOME=$HADOOP_HOME
    export HADOOP_PREFIX=$HADOOP_HOME
fi

# http://stackoverflow.com/questions/7134723/hadoop-on-osx-unable-to-load-realm-info-from-scdynamicstore
export HADOOP_OPTS="-Djava.security.krb5.realm= -Djava.security.krb5.kdc="

# Cloudera setup
if [ -f ~/cloudera/bashrc ]; then
    . ~/cloudera/bashrc
fi

# Docker
# http://viget.com/extend/how-to-use-docker-on-os-x-the-missing-guide
docker-ip() {
  boot2docker ip 2> /dev/null
}

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
    xterm-color) color_prompt=yes;;
esac

# uncomment for a colored prompt, if the terminal has the capability; turned
# off by default to not distract the user: the focus in a terminal window
# should be on the output of commands, not on the prompt
#force_color_prompt=yes

if [ -n "$force_color_prompt" ]; then
    if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
        # We have color support; assume it's compliant with Ecma-48
        # (ISO/IEC-6429). (Lack of such support is extremely rare, and such
        # a case would tend to support setf rather than setaf.)
        color_prompt=yes
    else
        color_prompt=
    fi
fi

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "$debian_chroot" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

if [ "$color_prompt" = yes ]; then
    PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
else
    PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi

# If this is an xterm set the title to user@host:dir
case "$TERM" in
    xterm*|rxvt*)
        PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
        ;;
    *)
        ;;
esac

# Regular Colors
Black="\[\033[0;30m\]"        # Black
Red="\[\033[0;31m\]"          # Red
BRed="\[\033[1;31m\]"         # Bold red
Green="\[\033[0;32m\]"        # Green
BGreen="\[\033[1;32m\]"       # Bold green
Yellow="\[\033[0;33m\]"       # Yellow
BYellow="\[\033[1;33m\]"      # Bold yellow
Cyan="\[\033[0;36m\]"         # Cyan
Gray="\[\033[1;30m\]"         # Gray
White="\[\033[0;37m\]"        # White
NO_COLOR="\[\033[0m\]"

# Prompt separator
#  This will go between the git indicators and the dollar sign.  It's empty by default,
#  but something I commonly do in the shell is to assign a newline to it, so you have
#  a status line, and then the prompt where you type your command is on the next line.
#
# Example:
#     [12:38:13] user@hostname example_repo (master)*$ SEP="
#     > "
#     [12:41:54] user@hostname example_repo (master)*
#     $

SEP=""

export PS1="\
$Gray[\t] \
$Green\u@\h \
$Yellow\W \
\$(\
    # get the reference description
    if refname=\$(git name-rev --name-only HEAD 2> /dev/null); then\
        # on a branch
        if curbranch=\$(git symbolic-ref HEAD 2> /dev/null); then\
            echo -n '$Cyan('\${curbranch##refs/heads/}')';\
        # detached head
        else\
            # unreachable
            if [ \$refname = 'undefined' ]; then\
                echo -n '$BRed(Unreachable detached HEAD: '\$(git rev-parse HEAD | head -c7)')';\
            # reachable
            else\
                echo -n '$White('\$(git rev-parse HEAD | head -c7)': '\$refname')';\
            fi;\
        fi;\
        git diff --quiet --cached &> /dev/null \
            || echo -n '$BGreen*';\
        git diff --quiet &> /dev/null \
            || echo -n '$BRed*';\
  git status --porcelain 2> /dev/null | grep -q ^?? \
        && echo -n '$Gray*';\
        echo -n ' ';\
    fi\
)\
$White\$SEP\
\$(\
    if [ \$USER = 'root' ]; then\
        echo -n '$Yellow#';\
    else\
        echo -n '$Green$';\
    fi;\
)\
$NO_COLOR "

unset color_prompt force_color_prompt
