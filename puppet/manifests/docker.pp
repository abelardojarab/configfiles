class docker {
  include apt

  # Prereqs (keep it minimal; do NOT include apt-transport-https)
  package { ['ca-certificates']:
    ensure => installed,
  } ->

  # Single owner of the repo (no separate apt::key)
  apt::source { 'docker':
    location     => 'https://download.docker.com/linux/ubuntu',
    release      => $facts['lsbdistcodename'],
    repos        => 'stable',
    key          => {
      id     => '9DC858229FC7DD38854AE2D88D81803C0EBFCD88',
      source => 'https://download.docker.com/linux/ubuntu/gpg',
    },
    include      => { src => false },
  } ~> Class['apt::update']

  # Ensure docker packages run after apt update
  package { [
    'docker-ce','docker-ce-cli','containerd.io',
    'docker-buildx-plugin','docker-compose-plugin',
  ]:
    ensure  => installed,
    require => Class['apt::update'],
  }
}
