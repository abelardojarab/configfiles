include apt

class golang {
  apt::ppa { 'ppa:longsleep/golang-backports':
  } ->

  package { 'golang-go':
    ensure => installed,
  }
}
