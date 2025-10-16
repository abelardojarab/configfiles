include apt

class tools {
  apt::ppa { 'ppa:ubuntuhandbook1/gimp':
  }

  apt::ppa { 'ppa:libreoffice/ppa':
  }

  apt::ppa { 'ppa:npalix/coccinelle':
  } ->

  # package { 'coccinelle':
  #   ensure => installed,
  # }

  apt::ppa { 'ppa:jonathonf/vim':
  } ->

  package { 'vim':
    ensure => installed,
  }

  apt::ppa { 'ppa:neovim-ppa/stable':
  } ->

  package { 'neovim':
    ensure => installed,
  }

  apt::ppa { 'ppa:kelleyk/emacs':
  } ->

  apt::ppa { 'ppa:ubuntuhandbook1/emacs':
  } ->

  package { [ "emacs28-nativecomp", "exuberant-ctags", "global", "libtree-sitter0", "libtree-sitter-dev" ]:
    ensure => installed,
  }

  package { [ "texlive-base", "texlive-lang-english", "texmaker" ]:
    ensure => installed,
  }

  apt::ppa { 'ppa:shutter/ppa':
  } ->

  package { [ "shutter" ]:
    ensure => installed,
  }

  apt::ppa { 'ppa:ubuntuhandbook1/vlc':
  } ->

  package { [ "vlc" ]:
    ensure => installed,
  }

  apt::ppa { 'ppa:aslatter/ppa':
  }

}
