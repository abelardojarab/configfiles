class docker {
  include apt

  # Prereqs (keep it minimal; do NOT include apt-transport-https)
  package { ['ca-certificates']:
    ensure => installed,
  } ->

  # Single owner of the repo. Keyring-based key (no apt_key/apt-key
  # dependency, matches telegraf.pp) since apt-key is gone on newer Ubuntu.
  apt::source { 'docker':
    location     => 'https://download.docker.com/linux/ubuntu',
    release      => $facts['lsbdistcodename'],
    repos        => 'stable',
    key          => {
      name   => 'docker.asc',
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
