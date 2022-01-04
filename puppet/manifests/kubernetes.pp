include apt

class kubernetes {
    apt::key {'kubernetes-repository':
        ensure => present,
        id     => '7F92E05B31093BEF5A3C2D38FEEA9169307EA071',
        source => 'https://packages.cloud.google.com/apt/doc/apt-key.gpg',
    } ->

    apt::source {'kubernetes':
        comment  => 'Kubernetes repository',
        location => 'http://apt.kubernetes.io/',
        repos    => 'kubernetes-xenial main',
        release  => '',
        key => {
            'id' => '7F92E05B31093BEF5A3C2D38FEEA9169307EA071',
        },
        include => {
            'deb' => true,
        },
    } ->

    package {'kubelet':
        ensure => installed,
    }

    package {'kubeadm':
        ensure => installed,
    }

    package {'kubectl':
        ensure => installed,
    }
}
