# ~/.bashrc
# shellcheck shell=bash
# shellcheck disable=SC1090

# Only for interactive shells
[[ $- != *i* ]] && return

#### Quality-of-life / safety ##################################################
# Readline niceties
bind "set completion-ignore-case on"
bind "set completion-map-case on"
bind "set show-all-if-ambiguous on"

# History: big, timestamped, shared across terms
export HISTCONTROL=ignoreboth
export HISTIGNORE="&:ls:[bf]g:[cb]d:b:history:exit:[ ]*"
shopt -s histappend cmdhist
export HISTSIZE=50000 HISTFILESIZE=50000
MY_BASH_BLUE=$'\033[0;34m'
MY_BASH_NOCOLOR=$'\033[0m'
export HISTTIMEFORMAT="${MY_BASH_BLUE}[%F %T] ${MY_BASH_NOCOLOR}"

# Window size autoupdate
shopt -s checkwinsize

# Less filter
command -v lesspipe >/dev/null 2>&1 && eval "$(SHELL=/bin/sh lesspipe)"

#### Helpers (no-op if already present) ########################################
# Dedup paths / license vars and prepend safely.
_path_prepend() {
  local d="$1" v="${2:-PATH}"
  [[ -d "$d" ]] || return 0
  local current sep=":"
  current="${!v}${sep}"
  case "${sep}${current}" in
    *"${sep}${d}${sep}"*) ;; # already there
    *) eval "export ${v}=\"${d}${sep}\${${v}}\"" ;;
  esac
}

_export_unique_append() {
  # _export_unique_append VAR value  (dedup ':'-list)
  local var="$1" add="$2" sep=":"
  local cur="${!var}"
  [[ -n "$add" ]] || return 0
  [[ "${sep}${cur}${sep}" == *"${sep}${add}${sep}"* ]] && return 0
  eval "export ${var}=\"\${${var}:+\${${var}}:}${add}\""
}

#### Colors used in PS1 ########################################################
BRed="\[\033[1;31m\]"
Green="\[\033[0;32m\]"
Yellow="\[\033[0;33m\]"
Cyan="\[\033[0;36m\]"
White="\[\033[0;37m\]"
Blue="\[\033[0;34m\]"
NO_COLOR="\[\033[0m\]"
SEP=""

#### Core aliases ##############################################################
# ls colors
if command -v dircolors >/dev/null 2>&1; then
  if [[ -r ~/.dircolors ]]; then
    eval "$(dircolors -b ~/.dircolors)"
  else
    eval "$(dircolors -b)"
  fi
  export LS_COLORS='di=34:ln=36:so=0:pi=0:ex=32:bd=0:cd=0:su=0:sg=0:tw=34:ow=34:'
  alias ls='ls --color=auto'
  alias grep='grep --color=auto'
  alias fgrep='fgrep --color=auto'
  alias egrep='egrep --color=auto'
fi
alias ll='ls -alF'; alias la='ls -A'; alias l='ls -CF'

# Tools
alias gpg='gpg'  # modern distros ship gpg v2 as 'gpg'
alias curl='curl --insecure'  # DANGEROUS: Disables TLS verification!

# rsync helpers
alias rsynccopy="rsync --partial --progress --append --rsh=ssh -r -h "
alias rsyncmove="rsync --partial --progress --append --rsh=ssh -r -h --remove-sent-files"

# Misc
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" \
  "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'
alias psudo='sudo -E env "PATH=$PATH LD_LIBRARY_PATH=$LD_LIBRARY_PATH"'

# Separate alias file
[[ -f ~/.bash_aliases ]] && . ~/.bash_aliases

show-empty-folders() { find . -depth -type d -empty; }

# Bash completion (optional)
if ! shopt -oq posix && [[ -f /etc/bash_completion ]]; then
  # shellcheck disable=SC1091
  . /etc/bash_completion
fi

#### Environment / tooling #####################################################
export SW="$HOME/sw"
export CTEST_OUTPUT_ON_FAILURE=1
export VAGRANT_LOG=error
export VAGRANT_DEFAULT_PROVIDER=libvirt
export LIBVIRT_DEFAULT_URI=qemu:///system
export GDK_CORE_DEVICE_EVENTS=1
export QT_USE_NATIVE_WINDOWS=1
export QT_X11_NO_MITSHM=1
export QT_QPA_PLATFORM=xcb
export QT_DEBUG_PLUGINS=0
export VISUAL=vim; export EDITOR="$VISUAL"

# Local paths (dedup-safe)
_path_prepend "$HOME/.local/bin"
_path_prepend "$HOME/.cask/bin"

# Emacs client alias (prefer system paths if present)
if command -v /usr/local/bin/emacsclient >/dev/null 2>&1; then
  alias emacsclients='/usr/local/bin/emacsclient -c -s ~/.emacs.cache/server/server'
elif command -v /usr/bin/emacsclient >/dev/null 2>&1; then
  alias emacsclients='/usr/bin/emacsclient -c -s ~/.emacs.cache/server/server'
else
  alias emacsclients='emacsclient -c -s ~/.emacs.cache/server/server'
fi
export EMACS_SERVER_FILE="$HOME/.emacs.cache/server/server"

# Licenses — keep list unique as we append many vendors
theHost="$(hostname)"
export theHost
_export_unique_append LM_LICENSE_FILE "47323@localhost"

# Java (prefer newer if present)
if [[ -d /usr/lib/jvm/java-17-oracle ]]; then
  export JAVA_HOME=/usr/lib/jvm/java-17-oracle
  export CLASSPATH=".:$JAVA_HOME/lib/tools.jar:$JAVA_HOME/lib/dt.jar"
elif [[ -d /usr/lib/jvm/java-9-oracle ]]; then
  export JAVA_HOME=/usr/lib/jvm/java-9-oracle
fi

export FILEBOT_OPTS="-Dnet.filebot.UserFiles.fileChooser=Swing"

# Intel Parallel Studio (source if exists)
for INTELPARALLELSTUDIO in /opt/intel/parallel_studio_xe_2020 /opt/intel/parallel_studio_xe_2018; do
  if [[ -f "$INTELPARALLELSTUDIO/psxevars.sh" ]]; then
    # shellcheck disable=SC1091
    . "$INTELPARALLELSTUDIO/psxevars.sh"
    break
  fi
done

# NVIDIA tuning env (kept as-is)
export GPU_FORCE_64BIT_PTR=0
export GPU_MAX_HEAP_SIZE=100
export GPU_USE_SYNC_OBJECTS=1
export GPU_MAX_ALLOC_PERCENT=95
export GPU_SINGLE_ALLOC_PERCENT=100

# CUDA 11.3
if [[ -d /usr/local/cuda-11.3 ]]; then
  export CUDADIR=/usr/local/cuda-11.3
  _path_prepend "$CUDADIR/bin"
  _export_unique_append LD_LIBRARY_PATH "$CUDADIR/lib64"
  export CUDA_HOME="$CUDADIR" CUDA_TOOLKIT_ROOT_DIR="$CUDADIR"
fi

# CUDA 12.2 (wins if present)
export CUDA_VERSION=12.2
if [[ -d "/usr/local/cuda-$CUDA_VERSION" ]]; then
  export CUDADIR="/usr/local/cuda-$CUDA_VERSION"
  _path_prepend "$CUDADIR/bin"
  _export_unique_append LD_LIBRARY_PATH "$CUDADIR/lib64"
  export CUDA_HOME="$CUDADIR" CUDA_TOOLKIT_ROOT_DIR="$CUDADIR"
fi
_export_unique_append LD_LIBRARY_PATH "/usr/lib/x86_64-linux-gnu"

#### Cadence (unchanged behavior, corrected vars) ##############################
export CDS_VERSION=IC618
if [[ -d "/opt/cadence/installs/$CDS_VERSION" ]]; then
  export CDS_AUTO_64BIT=NONE
  export CDSROOT="/opt/cadence/installs/$CDS_VERSION"
  export CDSHOME="$CDSROOT" CDS_ROOT="$CDSROOT"  # keep legacy vars
  export BASIC_LIB_PATH="$CDSROOT/tools/dfII/etc/cdslib/basic"
  export ANALOG_LIB_PATH="$CDSROOT/tools/dfII/etc/cdslib/artist/analogLib/"
  export CDS_LIC_FILE=27000@localhost
  export CDS_LOG_PATH=/tmp CDS_LOG_VERSION=pid
  export CDS_AUTO_CKOUT=all CDS_LOAD_ENV=CWD CDS_Netlisting_Mode=Analog
  export EDI_ROOT=/opt/cadence/installs/EDI131
  export MMSIM_ROOT=/opt/cadence/installs/MMSIM121
  _path_prepend "$MMSIM_ROOT/tools/bin"
  _path_prepend "$MMSIM_ROOT/tools/spectre/bin"
  _path_prepend "$CDS_ROOT/tools/bin"
  _path_prepend "$CDS_ROOT/tools/dfII/bin"
  _path_prepend "$EDI_ROOT/bin"
  _export_unique_append LM_LICENSE_FILE "$HOME/flexlm/cadence.dat"
  _export_unique_append MGLS_LICENSE_FILE "$HOME/flexlm/cadence.dat"

  export OA_UNSUPPORTED_PLAT=linux_rhel50_gcc44x
  export OA_HOME=/opt/cadence/installs/IC616/oa_v22.60.007
  export CDK_DIR=/opt/ncsu-cdk-1.6.0
  export PDK_DIR=/opt/FreePDK45
  export PDK_DIR_SC=/opt/FreePDK45StandardCells
fi

#### Apache/Ansys Totem ########################################################
if [[ -d "/opt/ansys/Totem/14.1.b2" ]]; then
  export TOTEM_VERSION=14.1.b2
  export APACHEDA_LICENSE_FILE="$HOME/flexlm/apache.dat"
  export APACHEROOT="/opt/ansys/Totem/$TOTEM_VERSION"
  _path_prepend "$APACHEROOT/bin"
  _export_unique_append LM_LICENSE_FILE "$HOME/flexlm/apache.dat"
fi

#### Synopsys ##################################################################
export SYNOPSYS=/opt/synopsys
_export_unique_append SNPSLMD_LICENSE_FILE "$HOME/flexlm/synopsys.dat"
_export_unique_append LM_LICENSE_FILE "$HOME/flexlm/synopsys.dat"

export DESIGN_COMPILER_VERSION=B-2008.09
export HSPICE_VERSION=F-2011.09-SP2
export STARRC_VERSION=H-2012.12
export COSMOSSCOPE_VERSION=H-2012.12
export ICWB_VERSION=G-2012.06-SP1
export ICV_VERSION=H-2013.06

export SNPS_DC_ROOT="/opt/synopsys/designcompiler/$DESIGN_COMPILER_VERSION"
export SNPS_HSPICE_ROOT="/opt/synopsys/hspice/$HSPICE_VERSION"
export SNPS_STARRC_ROOT="/opt/synopsys/starrc/$STARRC_VERSION"
export SNPS_COSMOSSCOPE_ROOT="/opt/synopsys/cosmosscope/$COSMOSSCOPE_VERSION"
export SNPS_ICWB_ROOT="/opt/synopsys/icweb/$ICWB_VERSION"
export SNPS_ICV_ROOT="/opt/synopsys/icvalidator/$ICV_VERSION"

[[ -d "$SNPS_DC_ROOT/bin" ]] && _path_prepend "$SNPS_DC_ROOT/bin"
[[ -d "$SNPS_HSPICE_ROOT/hspice/linux" ]] && _path_prepend "$SNPS_HSPICE_ROOT/hspice/linux"
[[ -d "$SNPS_STARRC_ROOT/bin" ]] && _path_prepend "$SNPS_STARRC_ROOT/bin"
[[ -d "$SNPS_COSMOSSCOPE_ROOT/ai_bin" ]] && _path_prepend "$SNPS_COSMOSSCOPE_ROOT/ai_bin"
[[ -d "$SNPS_ICWB_ROOT/bin/amd64" ]] && _path_prepend "$SNPS_ICWB_ROOT/bin/amd64"
[[ -d "$SNPS_ICV_ROOT/bin/SUSE.64" ]] && _path_prepend "$SNPS_ICV_ROOT/bin/SUSE.64"

#### Calibre ###################################################################
export CALIBRE_VERSION=2013.3_28.19
if [[ -d "/opt/mentor/calibre/$CALIBRE_VERSION" ]]; then
  export CALIBRE_HOME="/opt/mentor/calibre/$CALIBRE_VERSION"
  export MGC_HOME="$CALIBRE_HOME"
  _path_prepend "$CALIBRE_HOME/bin"
  _export_unique_append MGLS_LICENSE_FILE "$HOME/flexlm/calibre.dat"
  _export_unique_append LM_LICENSE_FILE "$HOME/flexlm/calibre.dat"
fi

#### Modelsim / Questa #########################################################
export QUESTASIM_VERSION=10.7c
if [[ -d "/opt/mentor/questasim/$QUESTASIM_VERSION/modeltech" ]]; then
  export MTI_HOME="/opt/mentor/questasim/$QUESTASIM_VERSION/modeltech"
  _path_prepend "$MTI_HOME/bin"
  _export_unique_append LM_LICENSE_FILE "$HOME/flexlm/modelsim.dat"
  _export_unique_append MGLS_LICENSE_FILE "$HOME/flexlm/modelsim.dat"
  export MTI_VCO_MODE=64 COMP64=1
fi

#### Precision #################################################################
export PRECISION_VERSION=2019.1
if [[ -d "/opt/mentor/precision/$PRECISION_VERSION" ]]; then
  _path_prepend "/opt/mentor/precision/$PRECISION_VERSION/bin"
  _export_unique_append LM_LICENSE_FILE "$HOME/flexlm/precision.dat"
  _export_unique_append MGLS_LICENSE_FILE "$HOME/flexlm/precision.dat"
fi

# Matlab
_path_prepend "/opt/Matlab/current/bin"
_export_unique_append LM_LICENSE_FILE "$HOME/flexlm/matlab.dat"

# Altera / Intel FPGA
host="$(hostname)"
case "$host" in
  ubuntu01) QUARTUS_VERSION=21.2 ;;
  ubuntu07) QUARTUS_VERSION=20.3 ;;
  ubuntu06) QUARTUS_VERSION=21.2 ;;
  *)        QUARTUS_VERSION=21.2 ;;
esac
if [[ -d "/opt/intelFPGA_pro/$QUARTUS_VERSION" ]]; then
  export QUARTUS_64BIT=1
  export QUARTUS_ROOT="/opt/intelFPGA_pro/$QUARTUS_VERSION"
  export QUARTUS_HOME="$QUARTUS_ROOT/quartus"
  export QUARTUS_ROOTDIR="$QUARTUS_HOME"
  _path_prepend "$QUARTUS_ROOT/quartus/bin"
  _path_prepend "$QUARTUS_ROOT/qsys/bin"
  export INTELFPGAOCLSDKROOT="$QUARTUS_ROOT/hld"
  _path_prepend "$INTELFPGAOCLSDKROOT/bin"
  _path_prepend "$INTELFPGAOCLSDKROOT/host/linux64/bin"
  export QSYS_ROOTDIR="$QUARTUS_ROOT/qsys/bin"
  _export_unique_append LM_LICENSE_FILE "$HOME/flexlm/altera.dat"
  _export_unique_append LM_LICENSE_FILE "$HOME/flexlm/altera_university.dat"
  export ALTERAOCLSDKROOT="$INTELFPGAOCLSDKROOT"
  _export_unique_append LD_LIBRARY_PATH "$INTELFPGAOCLSDKROOT/host/linux64/lib"
  _export_unique_append LD_LIBRARY_PATH "$INTELFPGAOCLSDKROOT/linux64/lib"
fi

# Xilinx
export XILINX_VERSION=2019.1
if [[ -d "/opt/Xilinx/Vivado/$XILINX_VERSION" ]]; then
  export XILINX_VIVADO="/opt/Xilinx/Vivado/$XILINX_VERSION"
  _path_prepend "$XILINX_VIVADO/bin"
  _path_prepend "/opt/Xilinx/SDK/$XILINX_VERSION/bin"
  export XILINX_SDX="/opt/Xilinx/SDx/$XILINX_VERSION"
  _path_prepend "$XILINX_SDX/bin"
  _export_unique_append LM_LICENSE_FILE "$HOME/flexlm/Xilinx.lic"
  export XILINX_XRT=/opt/xilinx/xrt
  _path_prepend "$XILINX_XRT/bin"
  _export_unique_append LD_LIBRARY_PATH "$XILINX_XRT/lib"
  export CPATH=/usr/include/x86_64-linux-gnu
fi

# Bitware
_path_prepend "/opt/bwtk/2018.6L/bin"

# Synopsys Synplify
export SYNPLIFY_VERSION="L-2016.03-SP1"
if [[ -d "/opt/synopsys/Synplify/$SYNPLIFY_VERSION/bin" ]]; then
  _export_unique_append SNPSLMD_LICENSE_FILE "$HOME/flexlm/synplify.dat"
  _path_prepend "/opt/synopsys/Synplify/$SYNPLIFY_VERSION/bin"
  _export_unique_append LM_LICENSE_FILE "$HOME/flexlm/synplify.dat"
fi

# SPSS / Sublime / PDF tools
_path_prepend "/opt/IBM/SPSS/Statistics/current/bin"
_path_prepend "/opt/sublime_text"
_path_prepend "/opt/master-pdf-editor-5"
_path_prepend "/opt/PDFStudio"

# Intel OpenCL SDK
if [[ -d /opt/intel/system_studio_2019/opencl-sdk ]]; then
  export INTEL_OCL_SDK=/opt/intel/system_studio_2019/opencl-sdk
  _path_prepend "${INTEL_OCL_SDK}/bin"
fi

# Perforce & Collaborator
if [[ -d /opt/perforce ]]; then
  _path_prepend "/opt/perforce/p4-2018.1/bin"
  export P4CLIENT=abelardojara-nvcpu P4EDITOR=vim P4PORT=p4hw:2001 P4USER=abelardoj
  _path_prepend "/opt/perforce/ccollab-cmdline.13.1.13400"
fi

# as2 & local bins
_path_prepend "/opt/nv/utils/as2/beta_0.4/bin"
_path_prepend "$HOME/bin/cmake/bin"
_path_prepend "/opt/scitools/Understand/current/bin/linux64"
_path_prepend "$HOME/go/bin"

# Node
export NPM_CONFIG_PREFIX="$HOME/.npm-global"
_path_prepend "$NPM_CONFIG_PREFIX/bin"
_path_prepend "$HOME/node_modules/npm/bin"

# Python (pyenv)
if [[ -d "$HOME/.pyenv" ]]; then
  export PYENV_ROOT="$HOME/.pyenv"
  _path_prepend "$PYENV_ROOT/bin"
  eval "$(pyenv init -)"
fi

# Other vars
export DLRM_DIR="$HOME/workspace/dlrm"
export OMP_NUM_THREADS=32
export MODEL_DIR=../../model
export DATA_DIR=./fake_criteo
ulimit -n 8192 2>/dev/null || true

# Poppy SSH
export POPPY_DIRECT_CONNECT=t

# Kubernetes
export KUBECONFIG="$HOME/.kube/config"
[[ -f "$HOME/.kube/nvidia" ]] && KUBECONFIG="$HOME/.kube/nvidia:$KUBECONFIG"
export KUBECONFIG
alias kubectl_get_pods_info='kubectl get pod -o=custom-columns=NAME:.metadata.name,STATUS:.status.phase,NODE:.spec.nodeName,IP:.status.podIP --all-namespaces -o wide'
alias kubectl_get_token='kubectl get secret -n kubernetes-dashboard $(kubectl get serviceaccount abelardojara -n kubernetes-dashboard -o jsonpath="{.secrets[0].name}") -o jsonpath="{.data.token}" | base64 --decode'

# Hadoop / Spark
export HADOOP_HOME=/opt/hadoop/current
_path_prepend "$HADOOP_HOME/bin"
export HADOOP_MAPRED_HOME=$HADOOP_HOME HADOOP_COMMON_HOME=$HADOOP_HOME YARN_HOME=$HADOOP_HOME
export HADOOP_COMMON_LIB_NATIVE_DIR="$HADOOP_HOME/lib/native"
export HADOOP_OPTS="-Djava.library.path=$HADOOP_HOME/lib"

export SPARK_HOME=/opt/spark/current
_path_prepend "$SPARK_HOME/bin"
export SPARK_MASTER_HOST='192.168.3.2'
export SPARK_WORKER_CORES=2 SPARK_WORKER_INSTANCES=2 SPARK_WORKER_MEMORY=2g
export PYSPARK_DRIVER_PYTHON="jupyter" PYSPARK_DRIVER_PYTHON_OPTS="notebook" PYSPARK_PYTHON=python3

# ==== Detect fd command (FreeBSD vs Linux) ====
if command -v fdfind >/dev/null 2>&1; then
    FD_CMD="fdfind"
elif command -v fd >/dev/null 2>&1; then
    FD_CMD="fd"
else
    FD_CMD=""
fi

# ==== Basic fd aliases ====
if [ -n "$FD_CMD" ]; then
    alias ff="$FD_CMD --type f --hidden --exclude .git"
    alias fdir="$FD_CMD --type d --hidden --exclude .git"
fi

# ==== Global GTAGS Configuration ====

# Single directory for both code symlinks and GTAGS database
export GTAGSROOT="$HOME/.gtags"

# Use exuberant-ctags parser
export GTAGSLABEL=ctags

# Initialize ~/.gtags directory and GTAGS database
_gtags_init() {
    if [ ! -d "$GTAGSROOT" ]; then
        echo "Creating $GTAGSROOT..."
        mkdir -p "$GTAGSROOT"
        echo "Add your source symlinks to $GTAGSROOT, then run: gupdate"
    fi

    if [ ! -f "$GTAGSROOT/GTAGS" ]; then
        if [ -z "$(ls -A "$GTAGSROOT" 2>/dev/null)" ]; then
            echo "⚠️  $GTAGSROOT is empty. Add symlinks to your source code first!"
            echo "Example: ln -s /usr/src/sys $GTAGSROOT/freebsd-sys"
            return 1
        fi
        echo "Generating GTAGS in $GTAGSROOT (this may take a while)..."
        (cd "$GTAGSROOT" && gtags --gtagslabel=ctags)
        echo "✓ GTAGS created successfully!"
    fi
}

# Update/regenerate GTAGS
gupdate() {
    if [ ! -d "$GTAGSROOT" ]; then
        _gtags_init
        return
    fi

    if [ ! -f "$GTAGSROOT/GTAGS" ]; then
        echo "Generating initial GTAGS..."
        (cd "$GTAGSROOT" && gtags -c --gtagslabel=ctags)
    else
        echo "Updating GTAGS..."
        (cd "$GTAGSROOT" && global -u)
    fi
    echo "✓ GTAGS updated!"
}

# Force full regeneration
gregenerate() {
    echo "Regenerating GTAGS from scratch..."
    rm -f "$GTAGSROOT/GTAGS" "$GTAGSROOT/GRTAGS" "$GTAGSROOT/GPATH"
    (cd "$GTAGSROOT" && gtags -c --gtagslabel=ctags)
    echo "✓ Done!"
}

# ==== TUI Functions ====

# Interactive symbol search with preview
gti() {
    _gtags_init || return 1
    local selected
    selected=$(global -c | fzf \
        --preview 'global -x -d {} 2>/dev/null | head -50' \
        --preview-window=right:60% \
        --height=60% \
        --header="Find symbol definition")
    [ -n "$selected" ] && global -x -d "$selected"
}

# Interactive reference search
gtir() {
    _gtags_init || return 1
    local selected
    selected=$(global -c | fzf \
        --preview 'global -x -r {} 2>/dev/null | head -50' \
        --preview-window=right:60% \
        --height=60% \
        --header="Find symbol references")
    [ -n "$selected" ] && global -x -r "$selected"
}

# File finder using fd with bat preview
gfile() {
    _gtags_init || return 1
    local selected preview_cmd

    if command -v bat >/dev/null 2>&1; then
        preview_cmd="bat --color=always --style=numbers --line-range=:100 {}"
    else
        preview_cmd="head -100 {}"
    fi

    if [ -n "$FD_CMD" ]; then
        # Use fd if available (faster)
        selected=$($FD_CMD --type f . "$GTAGSROOT" | \
            sed "s|^$GTAGSROOT/||" | \
            fzf --preview "$preview_cmd" --height=60% --header="Find file")
    else
        # Fall back to global -P
        selected=$(global -P | \
            fzf --preview "$preview_cmd" --height=60% --header="Find file")
    fi

    [ -n "$selected" ] && echo "$GTAGSROOT/$selected"
}

# Find file by name (fuzzy)
gfind() {
    _gtags_init || return 1
    local query="$*"
    local selected preview_cmd

    if command -v bat >/dev/null 2>&1; then
        preview_cmd="bat --color=always --style=numbers --line-range=:50 {}"
    else
        preview_cmd="head -50 {}"
    fi

    if [ -n "$FD_CMD" ]; then
        selected=$($FD_CMD --type f . "$GTAGSROOT" | \
            sed "s|^$GTAGSROOT/||" | \
            fzf --query="$query" \
                --preview "$preview_cmd" \
                --height=60% \
                --header="Find file by name")
    else
        selected=$(global -P | \
            fzf --query="$query" \
                --preview "$preview_cmd" \
                --height=60% \
                --header="Find file by name")
    fi

    if [ -n "$selected" ]; then
        # Open in $EDITOR or just show path
        if [ -n "$EDITOR" ]; then
            $EDITOR "$GTAGSROOT/$selected"
        else
            echo "$GTAGSROOT/$selected"
        fi
    fi
}

# Recent files (by modification time)
grecent() {
    _gtags_init || return 1
    local days="${1:-7}"
    local preview_cmd

    if command -v bat >/dev/null 2>&1; then
        preview_cmd="bat --color=always --style=numbers --line-range=:50 {}"
    else
        preview_cmd="head -50 {}"
    fi

    if [ -n "$FD_CMD" ]; then
        $FD_CMD --type f --changed-within "${days}d" . "$GTAGSROOT" | \
            sed "s|^$GTAGSROOT/||" | \
            fzf --preview "$preview_cmd" \
                --height=60% \
                --header="Files modified in last $days days"
    else
        find "$GTAGSROOT" -type f -mtime -"$days" | \
            sed "s|^$GTAGSROOT/||" | \
            fzf --preview "$preview_cmd" \
                --height=60% \
                --header="Files modified in last $days days"
    fi
}

# Both (definition + references)
gtib() {
    _gtags_init || return 1
    local selected
    selected=$(global -c | fzf --height=40%)
    [ -z "$selected" ] && return

    echo "=== Definition ==="
    global -x -d "$selected"
    echo -e "\n=== References ==="
    global -x -r "$selected"
}

# ==== Auto-completion ====
_global_complete() {
    local cur
    cur=${COMP_WORDS[COMP_CWORD]}
    mapfile -t COMPREPLY < <(global -c "$cur" 2>/dev/null)
}

_gfile_complete() {
    local cur
    cur=${COMP_WORDS[COMP_CWORD]}
    mapfile -t COMPREPLY < <(global -P "$cur" 2>/dev/null)
}

complete -F _global_complete global gti
complete -F _gfile_complete gfile

# Aliases
alias gdef='global -d'
alias gref='global -r'
complete -F _global_complete gdef gref

# Guix
_path_prepend "$HOME/.config/guix/current/bin"
export INFOPATH="$HOME/.config/guix/current/share/info:${INFOPATH}"
if [[ -d $HOME/.guix-profile ]]; then
  # shellcheck disable=SC1091
  . "$HOME/.guix-profile/etc/profile"
fi
[[ ! -d $HOME/.guix-profile/share/emacs ]] && unset EMACSLOADPATH

# Snap / Flatpak
_path_prepend "/snap/bin"
_path_prepend "/var/lib/flatpak/exports/bin"

# Local override
if [[ -f "$HOME/.bashrc_local" ]]; then
  # shellcheck disable=SC1091
  . "$HOME/.bashrc_local"
fi

# TERM / truecolor (prefer tmux-256color inside tmux)
if [[ -n "$TMUX" ]]; then
  if infocmp tmux-256color >/dev/null 2>&1; then
    export TERM=tmux-256color
  else
    export TERM=screen-256color
  fi
else
  if [[ -f /usr/share/terminfo/x/xterm-256color || -f /usr/lib/terminfo/x/xterm-256color ]]; then
    export TERM=xterm-256color
  else
    export TERM=xterm
  fi
fi
export COLORTERM=truecolor

#### Prompt ####################################################################
set_prompt() {
  # shellcheck disable=SC2154
  export PS1="\
${Blue}[\t] \
${Green}\u@\h \
${Yellow}[\w] \
\$( \
  if refname=\$(git name-rev --name-only HEAD 2>/dev/null); then \
    if curbranch=\$(git symbolic-ref -q --short HEAD 2>/dev/null); then \
      printf '${Cyan}(%s)' \"\$curbranch\"; \
    else \
      if [[ \$refname = 'undefined' ]]; then \
        printf '${BRed}(Unreachable detached HEAD: %s)' \"\$(git rev-parse --short=7 HEAD)\"; \
      else \
        printf '${White}(%s: %s)' \"\$(git rev-parse --short=7 HEAD)\" \"\$refname\"; \
      fi; \
    fi; \
    printf ' '; \
  fi \
)${White}${SEP}\
\$( if [[ \$USER = root ]]; then printf '${Yellow}#'; else printf '${Green}\$'; fi ) \
${NO_COLOR}"
  unset color_prompt force_color_prompt
}
export PROMPT_COMMAND=set_prompt

# Shared history maintenance (append to PROMPT_COMMAND)
export PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND$'\n'}history -a; history -c; history -r"

# vscode terminal default editor
[[ -n "$VSCODE_IPC_HOOK_CLI" ]] && export EDITOR="code -w"

# ssh-agent helper
if [[ -f "$HOME/workspace/configfiles/dotfiles/ssh-agent-manage.sh" ]]; then
  # shellcheck disable=SC1091
  . "$HOME/workspace/configfiles/dotfiles/ssh-agent-manage.sh"
fi
