class docker {
    include apt

    $prerequisites = ['apt-transport-https', 'ca-certificates']
    package {$prerequisites: ensure => installed} ->

    apt::key {'docker':
        ensure    => present,
        id        => '9DC858229FC7DD38854AE2D88D81803C0EBFCD88',
        options   => 'https://download.docker.com/linux/ubuntu/gpg',
    } ->

    apt::source {'docker':
        location  => 'https://download.docker.com/linux/ubuntu',
        repos     => 'stable',
        release   => $::lsbdistcodename,
    } ->

    package {'docker-ce':
        ensure  => 'latest',
    }

    package {'docker-compose':
        ensure => 'latest',
    }
}
