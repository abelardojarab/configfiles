include apt

class kubernetes {
  # Keyring-based key (no apt_key/apt-key dependency, matches telegraf.pp)
  apt::source { 'kubernetes':
    comment  => 'Kubernetes repository',
    location => 'https://pkgs.k8s.io/core:/stable:/v1.28/deb/',
    repos    => '/',
    release  => '',
    key      => {
      name   => 'kubernetes.asc',
      source => 'https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key',
    },
    include  => {
      'deb' => true,
    },
  } ~> Class['apt::update']

  package { ['kubelet', 'kubeadm', 'kubectl']:
    ensure  => installed,
    require => Class['apt::update'],
  }
}

