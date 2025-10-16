include snap

class snaps {
  package { 'libreoffice':
    ensure   => installed,
    provider => 'snap',
  }

  package { 'gimp':
    ensure   => installed,
    provider => 'snap',
  }

  package { 'inkscape':
    ensure   => installed,
    provider => 'snap',
  }

  package { 'universal-ctags':
    ensure   => installed,
    provider => 'snap',
  }

  package { 'rustup':
    ensure   => installed,
    provider => 'snap',
    install_options => ['classic'],
  }

  package { 'sublime-text':
    ensure   => installed,
    provider => 'snap',
    install_options => ['classic'],
  }

  package { 'codium':
    ensure   => installed,
    provider => 'snap',
    install_options => ['classic'],
  }

  # package { 'gitkraken':
  #   ensure   => installed,
  #   provider => 'snap',
  #   install_options => ['classic'],
  # }

  package { 'nvim':
    ensure   => installed,
    provider => 'snap',
    install_options => ['classic'],
  }

  package { 'emacs':
    ensure   => installed,
    provider => 'snap',
    install_options => ['classic'],
  }

  package { 'btop':
    ensure   => installed,
    provider => 'snap',
  }

  # amd64 only available snaps
  package { 'tmux':
    ensure   => installed,
    provider => 'snap',
    install_options => ['classic'],
  }

  package { 'pycharm-professional':
    ensure   => installed,
    provider => 'snap',
    install_options => ['classic'],
  }

  package { 'clion':
    ensure   => installed,
    provider => 'snap',
    install_options => ['classic'],
  }

  # package { 'code':
  #   ensure   => installed,
  #   provider => 'snap',
  #   install_options => ['classic'],
  # }

  # package { 'steam':
  #   ensure   => installed,
  #   provider => 'snap',
  # }

}
