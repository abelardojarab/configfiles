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

# No ._ files in archives please
export COPYFILE_DISABLE=true

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

# curl
alias curl='curl --insecure'

# rsync utilities
alias rsynccopy="rsync --partial --progress --append --rsh=ssh -r -h "
alias rsyncmove="rsync --partial --progress --append --rsh=ssh -r -h --remove-sent-files"

# Directory sizes
alias bigdir="du | sort -nr | cut -f2- | xargs du -hs | head -n 20"
alias bigdir1="du -d1 | sort -nr | cut -f2- | xargs du -hs | head -n 20"

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

# sudo alias
alias psudo='sudo -E env "PATH=$PATH LD_LIBRARY_PATH=$LD_LIBRARY_PATH"'

# Alias definitions.
# You may want to put all your additions into a separate file like
# ~/.bash_aliases, instead of adding them here directly.
# See /usr/share/doc/bash-doc/examples in the bash-doc package.

if [ -f ~/.bash_aliases ]; then
  . ~/.bash_aliases
fi

function show-empty-folders {
  find . -depth -type d -empty
}

# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if [ -f /etc/bash_completion ] && ! shopt -oq posix; then
  . /etc/bash_completion
fi

# Custom installs directory
SW=$HOME/sw

# Verbose ctest outputs
export CTEST_OUTPUT_ON_FAILURE=1

# Vagrant
export VAGRANT_LOG=error
export VAGRANT_DEFAULT_PROVIDER=libvirt
export LIBVIRT_DEFAULT_URI=qemu:///system

# Fix GTK3 scroll not working
export GDK_CORE_DEVICE_EVENTS=1

# Qt4 settings
export QT_USE_NATIVE_WINDOWS=1
export QT_X11_NO_MITSHM=1

# Qt5 sesttings
# available platforms: eglfs, linuxfb, minimal, vnc, xcb
export QT_QPA_PLATFORM=xcb
export QT_DEBUG_PLUGINS=0

# Editor setup
export VISUAL=vim
export EDITOR="$VISUAL"

# Local paths
export PATH=$HOME/.local/bin:$PATH

# Emacs settings
export EMACS_SERVER_FILE=$HOME/.emacs.cache/server/server
export PATH=$HOME/.cask/bin:$PATH

# Flexlm settings
export theHost=`hostname`
alias lmlicense='/opt/mentor/calibre/2013.3_28.19/bin/lmgrd -c'
export LM_LICENSE_FILE=47323@localhost:$LM_LICENSE_FILE

# Java options
if [ -d /usr/lib/jvm/java-9-oracle ]; then
  export JAVA_HOME=/usr/lib/jvm/java-9-oracle
fi
if [ -d /usr/lib/jvm/java-17-oracle ]; then
  export JAVA_HOME=/usr/lib/jvm/java-17-oracle
  CLASSPATH=.:$JAVA_HOME/lib/tools.jar:$JAVA_HOME/lib/dt.jar
  export CLASSPATH
fi

export FILEBOT_OPTS="-Dnet.filebot.UserFiles.fileChooser=Swing"

# Intel performance tools
if [ -f /opt/intel/parallel_studio_xe_2018/psxevars.sh ]; then
  export INTELPARALLELSTUDIO=/opt/intel/parallel_studio_xe_2018
  if [ -f $INTELPARALLELSTUDIO/psxevars.sh ]; then
    source $INTELPARALLELSTUDIO/psxevars.sh
  fi
fi
if [ -f /opt/intel/parallel_studio_xe_2020/psxevars.sh ]; then
  export INTELPARALLELSTUDIO=/opt/intel/parallel_studio_xe_2020
  if [ -f $INTELPARALLELSTUDIO/psxevars.sh ]; then
    source $INTELPARALLELSTUDIO/psxevars.sh
  fi
fi

# NVIDIA settings
export GPU_FORCE_64BIT_PTR=0
export GPU_MAX_HEAP_SIZE=100
export GPU_USE_SYNC_OBJECTS=1
export GPU_MAX_ALLOC_PERCENT=95
export GPU_SINGLE_ALLOC_PERCENT=100

# CUDA 10.2
if [ -d /usr/local/cuda-10.2 ]; then
  export PATH=/usr/local/cuda-10.2/bin:$PATH
  export CUDADIR=/usr/local/cuda-10.2
  export CUDA_HOME=$CUDADIR
  export CUDA_TOOLKIT_ROOT_DIR=$CUDADIR
  export LD_LIBRARY_PATH=$CUDADIR/lib64:$LD_LIBRARY_PATH
fi

# CUDA 11.2
export CUDA_VERSION=11.2
if [ -d /usr/local/cuda-$CUDA_VERSION ]; then
  export CUDADIR=/usr/local/cuda-$CUDA_VERSION
  export PATH=$CUDA_DIR/bin:$PATH
  export CUDA_HOME=$CUDADIR
  export CUDA_TOOLKIT_ROOT_DIR=$CUDADIR
  export LD_LIBRARY_PATH=$CUDADIR/lib64:$LD_LIBRARY_PATH
fi

# Cadence settings
export CDS_VERSION=IC618
if [ -d /opt/cadence/installs/$CDS_VERSION ]; then
  export CDS_AUTO_64BIT=NONE
  export CDSROOT=/opt/cadence/installs/$CDS_VERSION
  export CDSHOME=$CDS_ROOT
  export CDS_ROOT=$CDS_ROOT
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

  # OpenAccess
  export OA_UNSUPPORTED_PLAT=linux_rhel50_gcc44x
  export OA_HOME=/opt/cadence/installs/IC616/oa_v22.60.007

  # PDKs
  export CDK_DIR=/opt/ncsu-cdk-1.6.0
  export PDK_DIR=/opt/FreePDK45
  export PDK_DIR_SC=/opt/FreePDK45StandardCells
fi

# Apache settings
if [ -d /opt/ansys/Totem/$TOTEM_VERSION ]; then
  export TOTEM_VERSION=14.1.b2
  export APACHEDA_LICENSE_FILE=$HOME/flexlm/apache.dat
  export APACHEROOT=/opt/ansys/Totem/$TOTEM_VERSION
  export PATH=$APACHEROOT/bin:$PATH
  export LM_LICENSE_FILE=$LM_LICENSE_FILE:$HOME/flexlm/apache.dat
fi

# Synopsys settings
export SYNOPSYS=/opt/synopsys
export SNPSLMD_LICENSE_FILE=$HOME/flexlm/synopsys.dat
export LM_LICENSE_FILE=$LM_LICENSE_FILE:$HOME/flexlm/synopsys.dat

export DESIGN_COMPILER_VERSION=B-2008.09
export HSPICE_VERSION=F-2011.09-SP2
export STARRC_VERSION=H-2012.12
export COSMOSSCOPE_VERSION=H-2012.12
export ICWB_VERSION=G-2012.06-SP1
export ICV_VERSION=H-2013.06

export SNPS_DC_ROOT=/opt/synopsys/designcompiler/$DESIGN_COMPILER_VERSION
export SNPS_HSPICE_ROOT=/opt/synopsys/hspice/$HSPICE_VERSION
export SNPS_STARRC_ROOT=/opt/synopsys/starrc/$STARRC_VERSION
export SNPS_COSMOSSCOPE_ROOT=/opt/synopsys/cosmosscope/$COSMOSSCOPE_VERSION
export SNPS_ICWB_ROOT=/opt/synopsys/icweb/$ICWB_VERSION
export SNPS_ICV_ROOT=/opt/synopsys/icvalidator/$ICV_VERSION

if [ -d $SNPS_DC_ROOT/bin ]; then
  export PATH=$SNPS_DC_ROOT/bin:$PATH
fi
export PATH=$SNPS_HSPICE_ROOT/hspice/linux:$SNPS_STARRC_ROOT/bin:$SNPS_COSMOSSCOPE_ROOT/ai_bin:$PATH
export PATH=$SNPS_ICWB_ROOT/bin/amd64:$SNPS_ICV_ROOT/bin/SUSE.64:$PATH

# Calibre settings
export CALIBRE_VERSION=2013.3_28.19
if [ -d /opt/mentor/calibre/$CALIBRE_VERSION ]; then
  export CALIBRE_HOME=/opt/mentor/calibre/$CALIBRE_VERSION
  export MGC_HOME=$CALIBRE_HOME
  export PATH=$CALIBRE_HOME/bin:$PATH
  export MGLS_LICENSE_FILE=$HOME/flexlm/calibre.dat
  export LM_LICENSE_FILE=$LM_LICENSE_FILE:$HOME/flexlm/calibre.dat
fi

# Modelsim settings
export QUESTASIM_VERSION=10.7c
if [ -d MTI_HOME=/opt/mentor/questasim/$QUESTASIM_VERSION/modeltech ]; then
  export MTI_HOME=/opt/mentor/questasim/$QUESTASIM_VERSION/modeltech
  export PATH=$MTI_HOME/bin:$PATH
  export LM_LICENSE_FILE=$HOME/flexlm/modelsim.dat:$LM_LICENSE_FILE:
  export MGLS_LICENSE_FILE=$HOME/flexlm/modelsim.dat:$MGLS_LICENSE_FILE
  export MTI_VCO_MODE=64
  export COMP64=1
fi

# Precision settings
export PRECISSION_VERSION=2019.1
if [ -d /opt/mentor/precission/$PRECISSION_VERSION ]; then
  export PATH=/opt/mentor/precision/$PRECISSION_VERSION/bin:$PATH
  export LM_LICENSE_FILE=$HOME/flexlm/precision.dat:$LM_LICENSE_FILE:
  export MGLS_LICENSE_FILE=$HOME/flexlm/precision.dat:$MGLS_LICENSE_FILE
fi

# Matlab settings
export PATH=/opt/Matlab/current/bin:$PATH
export LM_LICENSE_FILE=$LM_LICENSE_FILE:$HOME/flexlm/matlab.dat

# Altera settings
export QUARTUS_VERSION=17.1
if [ -d /opt/intelFPGA_pro/$QUARTUS_VERSION ]; then
  export QUARTUS_64BIT=1
  export QUARTUS_ROOT=/opt/intelFPGA_pro/$QUARTUS_VERSION
  export QUARTUS_HOME=$QUARTUS_ROOT/quartus
  export QUARTUS_ROOTDIR=$QUARTUS_HOME
  export PATH=$QUARTUS_ROOT/quartus/bin:$QUARTUS_ROOT/qsys/bin:$PATH
  export INTELFPGAOCLSDKROOT=$QUARTUS_ROOT/hld
  export PATH=$PATH:$INTELFPGAOCLSDKROOT/bin
  export PATH=$INTELFPGAOCLSDKROOT/host/linux64/bin:$PATH
  export QSYS_ROOTDIR=$QUARTUS_ROOT/qsys/bin
  export LM_LICENSE_FILE=$HOME/flexlm/altera.dat:$LM_LICENSE_FILE
  export LM_LICENSE_FILE=$HOME/flexlm/altera_university.dat:$LM_LICENSE_FILE
  export ALTERAOCLSDKROOT=$INTELFPGAOCLSDKROOT
  export LD_LIBRARY_PATH=$INTELFPGAOCLSDKROOT/host/linux64/lib:$LD_LIBRARY_PATH
  export LD_LIBRARY_PATH=$INTELFPGAOCLSDKROOT/linux64/lib:$LD_LIBRARY_PATH
fi

# Xilinx settings
export XILINX_VERSION=2019.1
if [ -d /opt/Xilinx/Vivado/$XILINX_VERSION ]; then
  export XILINX_VIVADO=/opt/Xilinx/Vivado/$XILINX_VERSION
  export PATH=$PATH:$XILINX_VIVADO/bin
  export PATH=$PATH:/opt/Xilinx/SDK/$XILINX_VERSION/bin
  export XILINX_SDX=/opt/Xilinx/SDx/$XILINX_VERSION
  export PATH=$PATH:$XILINX_SDX/bin
  export LM_LICENSE_FILE=$LM_LICENSE_FILE:$HOME/flexlm/Xilinx.lic
  export XILINX_XRT=/opt/xilinx/xrt
  export PATH=$XILINX_XRT/bin:$PATH
  export LD_LIBRARY_PATH=$XILINX_XRT/lib:$LD_LIBRARY_PATH
  export CPATH=/usr/include/x86_64-linux-gnu
fi

# Bitware tools
export PATH=$PATH:/opt/bwtk/2018.6L/bin

# Synopsys Synplify
export SINPLIFY_VERSION=L-2016.03-SP1
if [ -d /opt/synopsys/Synplify/$SINPLIFY_VERSION/bin ]; then
  export SNPSLMD_LICENSE_FILE=$HOME/flexlm/synplify.dat
  export PATH=$PATH:/opt/synopsys/Synplify/$SINPLIFY_VERSION/bin
  export LM_LICENSE_FILE=$LM_LICENSE_FILE:$HOME/flexlm/synplify.dat
fi

# SPSS settings
export PATH=/opt/IBM/SPSS/Statistics/current/bin:$PATH

# Sublime Text settings
export PATH=/opt/sublime_text:$PATH

# Master PDF and PDF Studio
export PATH=/opt/master-pdf-editor-5:$PATH
export PATH=/opt/PDFStudio:$PATH

# Intel OpenCL compiler for x86
export INTEL_OCL_SDK_VERSION=2019
if [ -d /opt/intel/system_studio_$INTEL_OCL_SDK_VERSION/opencl-sdk ]; then
  export INTEL_OCL_SDK=/opt/intel/system_studio_$INTEL_OCL_SDK_VERSION/opencl-sdk
  export PATH=${PATH}:${INTEL_OCL_SDK}/bin
fi

# Perforce
if [ -d /opt/perforce ]; then
  export PATH=$PATH:/opt/perforce/p4-2018.1/bin
  export P4CLIENT=abelardojara-nvcpu
  export P4EDITOR=vim
  export P4PORT=p4hw:2001
  export P4USER=abelardoj
  export P4DIFF

  # ccollab
  export PATH=$PATH:/opt/perforce/ccollab-cmdline.13.1.13400
fi

# as2
if [ -d /opt/nv/utils/as2 ] ; then
  export PATH=$PATH:/opt/nv/utils/as2/beta_0.4/bin
fi
export PATH=$PATH:/home/nv/bin

# Set up general GTAGS location
export GTAGSLIBPATH=$HOME/.gtags/
export GTAGSTHROUGH=true
export GTAGSLABEL=exuberant-ctags
export GTAGSFORCECPP=1

# Go
export PATH=$HOME/go/bin:$PATH

# Node
export NPM_CONFIG_PREFIX=$HOME/.npm-global
export PATH=$NPM_CONFIG_PREFIX/bin:$PATH
export PATH=$PATH:$HOME/node_modules/npm/bin

# Python env
if [[ -d ${HOME}/.pyenv ]] ; then
  export PYENV_ROOT="${HOME}/.pyenv"
  export PATH="${PYENV_ROOT}/bin:${PATH}"
  eval "$(pyenv init -)"
fi

# Kubernetes
export KUBECONFIG=$HOME/.kube/config
if  [[ -f ${HOME}/.kube/nvidia ]] ; then
  export KUBECONFIG=$HOME/.kube/nvidia:$KUBECONFIG
fi
alias kubectl_get_pods_info='kubectl get pod -o=custom-columns=NAME:.metadata.name,STATUS:.status.phase,NODE:.spec.nodeName,IP:.status.podIP --all-namespaces'
alias kubectl_get_token='kubectl get secret -n kubernetes-dashboard $(kubectl get serviceaccount abelardojara -n kubernetes-dashboard -o jsonpath="{.secrets[0].name}") -o jsonpath="{.data.token}" | base64 --decode'

# Hadoop dev
export HADOOP_HOME=/opt/hadoop/current
export PATH=$PATH:$HADOOP_HOME/bin
export HADOOP_MAPRED_HOME=$HADOOP_HOME
export HADOOP_COMMON_HOME=$HADOOP_HOME
export YARN_HOME=$HADOOP_HOME
export HADOOP_COMMON_LIB_NATIVE_DIR=$HADOOP_HOME/lib/native
export HADOOP_OPTS="-Djava.library.path=$HADOOP_HOME/lib"

# Spark settings
export SPARK_HOME=/opt/spark/current
export PATH=$PATH:$SPARK_HOME/bin

# Spark cluster settings
export SPARK_MASTER_HOST='192.168.3.2'
export SPARK_WORKER_CORES=2
export SPARK_WORKER_INSTANCES=2
export SPARK_WORKER_MEMORY=2g

# PySpark
export PYSPARK_DRIVER_PYTHON="jupyter"
export PYSPARK_DRIVER_PYTHON_OPTS="notebook"
export PYSPARK_PYTHON=python3

# Understand tool
export PATH=$PATH:/opt/scitools/Understand/current/bin/linux64

# Guix
export PATH="$HOME/.config/guix/current/bin:$PATH"
export INFOPATH="$HOME/.config/guix/current/share/info:$INFOPATH"
if [[ -d $HOME/.guix-profile ]]; then
  export GUIX_PROFILE="$HOME/.guix-profile"
  . "$GUIX_PROFILE/etc/profile"
fi

# Snap
export PATH=/snap/bin:$PATH

# Local settings
if [ -f $HOME/.bashrc_local ]; then
  source ~/.bashrc_local
fi

# TERM
if [ -f /usr/share/terminfo/x/xterm-256color ]; then
  export TERM="xterm-256color"
else
  export TERM="xterm"
fi

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

LIGHTNING_BOLT="⚡"
UP_ARROW="↑"
DOWN_ARROW="↓"
UD_ARROW="↕"
FF_ARROW="→"
RECYCLE="♺"
MIDDOT="•"
PLUSMINUS="±"

# Prompt separator
SEP=""

function set_prompt {

  # create a $fill of all screen width minus the time string and a space:
  let fillsize=${COLUMNS}-11
  fill=""
  while [ "$fillsize" -gt "0" ]
  do
    fill="-${fill}" # fill with underscores to work on
    let fillsize=${fillsize}-1
  done

  # Prompt variable:
  export PS1="\
$Blue[\t] \
$Green\u@\h \
$Yellow[\w] \
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

}
export PROMPT_COMMAND=set_prompt

# After each command, append to the history file and reread it
export PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND$'\n'}history -a; history -c; history -r"
