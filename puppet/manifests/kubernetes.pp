include apt

class kubernetes {
  apt::key { 'kubernetes-repository':
    ensure => present,
    id     => '3F01618A51312F3F',
    source => 'https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key',
  } ->

  apt::source { 'kubernetes':
    comment  => 'Kubernetes repository',
    location => 'https://pkgs.k8s.io/core:/stable:/v1.28/deb/',
    repos    => '/',
    release  => '',
    key      => {
      'id'     => '3F01618A51312F3F',
      'source' => 'https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key',
    },
    include  => {
      'deb' => true,
    },
  } ->

  package { ['kubelet', 'kubeadm', 'kubectl']:
    ensure => installed,
    require => Apt::Source['kubernetes'],
  }
}

