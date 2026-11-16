#!/bin/sh
# Links dotfiles in the editor's home (/config) to the host's copies,
# which live under ~/workspace (mounted at the same path) just as the
# host's own ~/.inputrc, ~/.gnupg, ~/.fonts, ~/.vimrc and ~/.vim link
# there, so the editor's terminal and the host share one copy of each.
# linuxserver's init runs every script in /custom-cont-init.d as root at
# each container start, so the links come back after a recreate.
#
# A file or directory already in a link's place is renamed to
# <name>.pre-link.<timestamp>, never deleted. A link whose target is
# missing (the workspace not mounted) is skipped with a message, so
# nothing is moved aside for a dangling link.
workspace=/home/abelardojara/workspace

link() {
  name="/config/$1"
  target="$2"
  if [ ! -e "$target" ]; then
    echo "home-links: $target missing, $name not linked"
    return
  fi
  if [ -L "$name" ] && [ "$(readlink "$name")" = "$target" ]; then
    return
  fi
  if [ -e "$name" ] || [ -L "$name" ]; then
    mv "$name" "$name.pre-link.$(date +%Y%m%d%H%M%S)"
  fi
  ln -s "$target" "$name"
  chown -h abc:abc "$name"
}

link .inputrc "$workspace/configfiles/dotfiles/.inputrc"
link .gnupg "$workspace/Documents/GnuPG/.gnupg"
link .fonts "$workspace/configfiles/Fonts"
link .vimrc "$workspace/vim-config/.vimrc"
link .vim "$workspace/vim-config/.vim"
