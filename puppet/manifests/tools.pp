include apt

class tools {
    apt::ppa { 'ppa:neovim-ppa/stable':
    } ->

    package { 'neovim':
        ensure => installed,
    }

    apt::ppa { 'ppa:kelleyk/emacs':
    } ->

    package { [ "emacs27", "exuberant-ctags", "global" ]:
        ensure => installed,
    }

    package { [ "texlive-base", "texlive-lang-english", "pandoc", "graphviz", "imagemagick", "texmaker" ]:
        ensure => installed,
    }
}
